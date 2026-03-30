from data.faq_repository import get_all_faqs  
from core.retriever import FAQRetriever  
from core.llm_builder import get_faq_chain, get_llm
from config import settings  
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser # StrOutputParser 추가
from core.prompts import INTENT_CLASSIFIER_PROMPT, REWRITE_PROMPT # REWRITE_PROMPT 추가

class ChatService:
    """
    사용자 질문을 처리하는 핵심 비즈니스 로직.
    검증 -> 기록 변환 -> 의도 분류 -> 질문 재작성 -> 검색 -> 답변 생성 순으로 동작합니다.
    """
    def __init__(self):
        self.faqs = get_all_faqs() 
        self.retriever = FAQRetriever(self.faqs)  
        self.faq_chain = get_faq_chain()
        self.intent_chain = INTENT_CLASSIFIER_PROMPT | get_llm() | JsonOutputParser()
        
        # [핵심] 질문 재작성 전용 체인 추가
        self.rewrite_chain = REWRITE_PROMPT | get_llm() | StrOutputParser()

    def _validate_input(self, question: str):
        """사용자 입력값 가드레일"""
        q = question.strip()

        if not q:
            return False, settings.ERROR_MESSAGE_INPUT  
        if len(q) > 500:
            return False, settings.ERROR_MESSAGE_INPUT_TOO_LONG  
        if q.replace(" ", "").isdigit():
            return False, settings.ERROR_MESSAGE_INPUT  
        return True, q
    
    def get_response(self, message: str, history: list):
        is_valid, validated_q = self._validate_input(message)
        if not is_valid: 
            return validated_q 

        try:
            # ---------------------------------------------------------
            # Step 1. 대화 기록 변환 (Gradio -> LangChain)
            # ---------------------------------------------------------
            chat_history = []
            for msg in history:
                if isinstance(msg, dict):
                    if msg.get("role") == "user":
                        chat_history.append(HumanMessage(content=msg.get("content", "")))
                    elif msg.get("role") == "assistant":
                        chat_history.append(AIMessage(content=msg.get("content", "")))
                elif isinstance(msg, (list, tuple)) and len(msg) == 2:
                    chat_history.append(HumanMessage(content=msg[0])) 
                    chat_history.append(AIMessage(content=msg[1]))    

            # ---------------------------------------------------------
            # Step 2. 의도 분류 (Intent Classification)
            # ---------------------------------------------------------
            try:
                intent_res = self.intent_chain.invoke({
                    "message": validated_q, 
                    "history": chat_history
                })
                intent = intent_res.get("intent", "chitchat")
            except Exception:
                intent = "question"

            if intent == "greeting":
                return "안녕하세요! 디지털 헬스케어 AI 상담원입니다. 건강 관리나 앱 사용에 대해 무엇을 도와드릴까요?"
            elif intent == "complaint":
                return "이용에 불편을 드려 대단히 죄송합니다. 해당 문제는 신속하게 기술팀에 전달하여 조치하겠습니다."
            elif intent == "chitchat":
                return "ㅎㅎ 편하게 말씀해 주셔서 감사합니다. 헬스케어 관련 궁금증이 생기면 언제든 물어보세요!"

            # ---------------------------------------------------------
            # Step 3. 질문 재작성 (Query Rewriting)
            # ---------------------------------------------------------
            search_query = validated_q
            if chat_history:
                # 과거 대화가 있을 때만 재작성 로직을 태웁니다. (메모리 절약을 위해 최근 4개 메시지만 전달)
                search_query = self.rewrite_chain.invoke({
                    "history": chat_history[-4:], 
                    "question": validated_q
                })
                # 터미널에서 어떻게 질문이 변환되었는지 디버깅할 수 있습니다.
                print(f"🔄 [질문 재작성] 원본: '{validated_q}' -> 검색용: '{search_query}'") 

            # ---------------------------------------------------------
            # Step 4. 임계값(Threshold) 기반 검색
            # ---------------------------------------------------------
            # 💡 주의: 여기서 검색은 원본(validated_q)이 아닌 재작성된 질문(search_query)으로 합니다.
            # ---------------------------------------------------------
            # Step 4. 임계값(Threshold) 기반 검색
            # ---------------------------------------------------------
            docs_and_scores = self.retriever.vectorstore.similarity_search_with_score(search_query, k=2)

            if not docs_and_scores:
                return settings.ERROR_MESSAGE_NO_MATCH
            
            best_doc, best_score = docs_and_scores[0]
            
            # [수정 전] if best_score > 1.2:
            # [수정 후] 임계값을 1.5로 더 여유 있게 풀어줍니다.
            if best_score > 1.5:
                return "죄송합니다. 해당 질문은 디지털 헬스케어 FAQ 가이드에 포함되어 있지 않아 정확한 답변을 드릴 수 없습니다."

            matched_docs = [doc for doc, score in docs_and_scores]
            context_text = "\n\n".join([doc.page_content for doc in matched_docs])
            sources = [f"[{doc.metadata['category']}] {doc.metadata['id']}" for doc in matched_docs]

            # ---------------------------------------------------------
            # Step 5. LLM 답변 생성 (최종 렌더링)
            # ---------------------------------------------------------
            # 💡 주의: 답변을 생성할 때는 재작성된 딱딱한 질문이 아니라, 사용자가 입력한 자연스러운 원본 질문(validated_q)을 사용합니다.
            response = self.faq_chain.invoke({
                "context": context_text,   
                "question": validated_q,   
                "history": chat_history    
            })

            source_text = "\n\n**[참고 문서]**\n" + "\n".join([f"- {s}" for s in sources])
            return response + source_text
        
        except Exception as e:
            print(f"Error : {e}")
            return settings.ERROR_MESSAGE_SYSTEM