"""
LLM 객체 생성 및 LangChain 파이프라인(LCEL) 조립.

[설계 포인트] FAQ 응답 체인은 RunnableParallel 로 두 작업을 동시에 수행합니다.
  - answer  : [참고 문서]를 근거로 LLM 답변 생성 (FAQ_CHAT_PROMPT | llm | StrOutputParser)
  - sources : 검색된 문서의 메타데이터로 '참고 문서' 출처 블록 생성
두 결과를 RunnableLambda 로 합쳐 최종 문자열을 만듭니다. LLM 호출(느림)과
출처 포맷팅(빠름)이 분리되어 있어 구조가 명확하고 확장이 쉽습니다.
"""
from __future__ import annotations

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import Runnable, RunnableLambda, RunnableParallel

from config import settings
from core.prompts import FAQ_CHAT_PROMPT


def get_llm():
    """설정값에 기반하여 OpenAI LLM 객체를 생성합니다."""
    from langchain_openai import ChatOpenAI  # 지연 임포트(테스트 시 OpenAI 불필요)

    return ChatOpenAI(
        openai_api_key=settings.require_openai_api_key(),
        model=settings.LLM_MODEL_NAME,
        temperature=settings.LLM_TEMPERATURE,
    )


def format_sources(docs: list[Document]) -> str:
    """검색된 문서들에서 [카테고리] ID 형태의 출처 블록을 생성(중복 제거)."""
    if not docs:
        return ""
    seen: set[tuple[str, str]] = set()
    lines: list[str] = []
    for d in docs:
        category = d.metadata.get("category", "미분류")
        doc_id = d.metadata.get("id", "N/A")
        key = (category, doc_id)
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"- [{category}] {doc_id}")
    return "\n\n**[참고 문서]**\n" + "\n".join(lines)


def _combine(parts: dict) -> str:
    return parts["answer"] + parts["sources"]


def get_faq_chain() -> Runnable:
    """
    입력: {"context": str, "question": str, "history": list, "docs": list[Document]}
    출력: 답변 본문 + 참고 문서 블록이 합쳐진 최종 문자열.
    """
    llm = get_llm()

    answer_branch = FAQ_CHAT_PROMPT | llm | StrOutputParser()
    sources_branch = RunnableLambda(lambda x: format_sources(x.get("docs", [])))

    return (
        RunnableParallel(answer=answer_branch, sources=sources_branch)
        | RunnableLambda(_combine)
    )
