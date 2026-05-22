"""
사용자 질문 처리 핵심 비즈니스 로직.
검증 → 기록 변환 → 의도 분류 → 질문 재작성 → (임계값) 검색 → 답변 생성 순으로 동작합니다.
"""
from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser

from config import settings
from core.llm_builder import get_faq_chain, get_llm
from core.prompts import INTENT_CLASSIFIER_PROMPT, REWRITE_PROMPT
from core.retriever import FAQRetriever
from data.faq_repository import get_all_faqs


class ChatService:
    def __init__(self, retriever: FAQRetriever | None = None):
        self.faqs = get_all_faqs()
        # 리트리버 주입 가능(테스트에서 FakeEmbeddings 기반 리트리버 사용)
        self.retriever = retriever or FAQRetriever(self.faqs)
        self.faq_chain = get_faq_chain()
        self.intent_chain = INTENT_CLASSIFIER_PROMPT | get_llm() | JsonOutputParser()
        self.rewrite_chain = REWRITE_PROMPT | get_llm() | StrOutputParser()

    # -- guardrail ---------------------------------------------------------
    def _validate_input(self, question: str):
        q = (question or "").strip()
        if not q:
            return False, settings.ERROR_MESSAGE_INPUT
        if len(q) > 500:
            return False, settings.ERROR_MESSAGE_INPUT_TOO_LONG
        if q.replace(" ", "").isdigit():
            return False, settings.ERROR_MESSAGE_INPUT
        return True, q

    @staticmethod
    def _to_langchain_history(history: list) -> list:
        """Gradio 대화 기록(dict 또는 [user, assistant] 튜플)을 LangChain 메시지로 변환."""
        chat_history = []
        for msg in history or []:
            if isinstance(msg, dict):
                role, content = msg.get("role"), msg.get("content", "")
                if role == "user":
                    chat_history.append(HumanMessage(content=content))
                elif role == "assistant":
                    chat_history.append(AIMessage(content=content))
            elif isinstance(msg, (list, tuple)) and len(msg) == 2:
                chat_history.append(HumanMessage(content=msg[0]))
                chat_history.append(AIMessage(content=msg[1]))
        return chat_history

    def _classify_intent(self, question: str, chat_history: list) -> str:
        try:
            res = self.intent_chain.invoke({"message": question, "history": chat_history})
            return res.get("intent", "question")
        except Exception:
            # 분류 실패 시 질문으로 간주(검색을 시도하는 편이 안전)
            return "question"

    def _rewrite_query(self, question: str, chat_history: list) -> str:
        if not chat_history:
            return question
        rewritten = self.rewrite_chain.invoke(
            {"history": chat_history[-settings.REWRITE_HISTORY_WINDOW:], "question": question}
        ).strip()
        if not rewritten:  # LLM 이 빈 문자열을 주면 원본 사용
            rewritten = question
        print(f"🔄 [질문 재작성] 원본: '{question}' -> 검색용: '{rewritten}'")
        return rewritten

    # -- main --------------------------------------------------------------
    def get_response(self, message: str, history: list) -> str:
        is_valid, validated_q = self._validate_input(message)
        if not is_valid:
            return validated_q

        try:
            chat_history = self._to_langchain_history(history)

            # Step 2. 의도 분류
            intent = self._classify_intent(validated_q, chat_history)
            canned = {
                "greeting": "안녕하세요! 디지털 헬스케어 AI 상담원입니다. 건강 관리나 앱 사용에 대해 무엇을 도와드릴까요?",
                "complaint": "이용에 불편을 드려 대단히 죄송합니다. 해당 문제는 신속하게 기술팀에 전달하여 조치하겠습니다.",
                "chitchat": "ㅎㅎ 편하게 말씀해 주셔서 감사합니다. 헬스케어 관련 궁금증이 생기면 언제든 물어보세요!",
            }
            if intent in canned:
                return canned[intent]

            # Step 3. 질문 재작성 (멀티턴 문맥 보강)
            search_query = self._rewrite_query(validated_q, chat_history)

            # Step 4. 임계값 기반 검색 (재작성된 질문으로 검색)
            docs_and_scores = self.retriever.search_with_score(
                search_query, top_k=settings.RETRIEVER_TOP_K
            )
            if not docs_and_scores:
                return settings.ERROR_MESSAGE_NO_MATCH

            best_score = docs_and_scores[0][1]
            if best_score > settings.RETRIEVER_SCORE_THRESHOLD:
                # 가장 가까운 문서조차 임계값 밖 → 도메인 밖(OOD) 질문으로 거부
                return settings.ERROR_MESSAGE_OOD

            # 임계값 안에 든 문서만 컨텍스트/출처에 사용(엉뚱한 2순위 문서 혼입 방지)
            matched_docs = [
                doc for doc, score in docs_and_scores
                if score <= settings.RETRIEVER_SCORE_THRESHOLD
            ]
            context_text = "\n\n".join(doc.page_content for doc in matched_docs)

            # Step 5. LLM 답변 생성 (RunnableParallel: 답변 + 출처). 답변은 원본 질문 사용.
            return self.faq_chain.invoke({
                "context": context_text,
                "question": validated_q,
                "history": chat_history,
                "docs": matched_docs,
            })

        except Exception as e:
            print(f"Error : {e}")
            return settings.ERROR_MESSAGE_SYSTEM
