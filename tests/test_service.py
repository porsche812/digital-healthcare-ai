"""
ChatService 오케스트레이션 통합 테스트 (네트워크/비용 0).

LLM 체인(의도분류/재작성/답변생성)을 스텁으로 대체하고, 결정적 임베딩 리트리버를
주입하여 흐름 전체(의도 라우팅 → 재작성 → 임계값 검색 → 출처 표기/거부)를 검증한다.
"""
import pytest

from config import settings
from core.llm_builder import format_sources
from core.retriever import FAQRetriever
from service.chat_service import ChatService
from tests.test_retriever import FAQS, CharBagEmbeddings


class StubChain:
    """invoke 호출 시 미리 정한 값을 반환하는 가짜 체인."""
    def __init__(self, value):
        self.value = value
        self.calls = []

    def invoke(self, inputs):
        self.calls.append(inputs)
        return self.value(inputs) if callable(self.value) else self.value


def make_service(intent="question", rewrite=None, monkeypatch=None, tmp_path=None):
    monkeypatch.setattr(settings, "VECTOR_STORE_PATH", str(tmp_path / "idx"))
    svc = ChatService.__new__(ChatService)  # __init__ 우회(OpenAI 미사용)
    svc.faqs = FAQS
    svc.retriever = FAQRetriever(FAQS, embeddings=CharBagEmbeddings())
    svc.intent_chain = StubChain({"intent": intent})
    svc.rewrite_chain = StubChain(rewrite or (lambda x: x["question"]))
    # 답변 체인: 본문 + 실제 출처 포맷을 합쳐 반환(서비스가 docs 를 잘 넘기는지 검증)
    svc.faq_chain = StubChain(lambda x: "답변본문" + format_sources(x["docs"]))
    return svc


def test_greeting_returns_canned(monkeypatch, tmp_path):
    svc = make_service(intent="greeting", monkeypatch=monkeypatch, tmp_path=tmp_path)
    out = svc.get_response("안녕하세요", [])
    assert "디지털 헬스케어 AI 상담원입니다" in out


def test_complaint_returns_apology(monkeypatch, tmp_path):
    svc = make_service(intent="complaint", monkeypatch=monkeypatch, tmp_path=tmp_path)
    assert "죄송합니다" in svc.get_response("앱이 자꾸 튕겨서 짜증나요", [])


def test_empty_input_short_circuits(monkeypatch, tmp_path):
    svc = make_service(monkeypatch=monkeypatch, tmp_path=tmp_path)
    assert svc.get_response("   ", []) == settings.ERROR_MESSAGE_INPUT


def test_question_returns_answer_with_sources(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "RETRIEVER_SCORE_THRESHOLD", 9999)  # 통과 보장
    svc = make_service(intent="question", monkeypatch=monkeypatch, tmp_path=tmp_path)
    out = svc.get_response("검진 전 금식 시간 알려줘", [])
    assert "답변본문" in out
    assert "[참고 문서]" in out  # 출처 블록 포함


def test_ood_rejected_when_above_threshold(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "RETRIEVER_SCORE_THRESHOLD", 0.0)  # 무엇이든 임계값 초과
    svc = make_service(intent="question", monkeypatch=monkeypatch, tmp_path=tmp_path)
    out = svc.get_response("아무 질문", [])
    assert out == settings.ERROR_MESSAGE_OOD


def test_rewrite_invoked_only_with_history(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "RETRIEVER_SCORE_THRESHOLD", 9999)
    svc = make_service(intent="question", rewrite=lambda x: "재작성된 질문",
                       monkeypatch=monkeypatch, tmp_path=tmp_path)
    # 히스토리 없음 → 재작성 스킵
    svc.get_response("금식 시간?", [])
    assert len(svc.rewrite_chain.calls) == 0
    # 히스토리 있음 → 재작성 호출
    svc.get_response("그럼 물은?", [{"role": "user", "content": "검진 금식"},
                                    {"role": "assistant", "content": "8시간"}])
    assert len(svc.rewrite_chain.calls) == 1


def test_history_tuple_format_supported(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "RETRIEVER_SCORE_THRESHOLD", 9999)
    svc = make_service(intent="question", monkeypatch=monkeypatch, tmp_path=tmp_path)
    out = svc.get_response("금식 시간?", [("이전 질문", "이전 답변")])  # 레거시 튜플
    assert "답변본문" in out
