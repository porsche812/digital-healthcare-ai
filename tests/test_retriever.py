"""
FAISS 리트리버 테스트 (OpenAI 불필요).

결정적(deterministic) 임베딩을 주입하여:
  - 인덱스 빌드 → 디스크 저장 → 재로드(데이터 동일 시) → 자동 재빌드(데이터 변경 시)
  - similarity_search_with_score 의 거리 동작(유사 질문은 가깝고 무관 질문은 멀다)
를 네트워크/비용 없이 검증한다.
"""
import re

import pytest
from langchain_core.embeddings import Embeddings

from config import settings
from core.retriever import FAQRetriever, _fingerprint

# 한글 문자 단위 bag-of-chars 임베딩용 고정 어휘
_VOCAB = list("위내시경금식수면운전약혈압예방접종검진보험청구병원예약")


class CharBagEmbeddings(Embeddings):
    """문자 출현 빈도 기반 결정적 임베딩. 의미적으로 유사하면 가깝게 나온다."""

    def _vec(self, text: str) -> list[float]:
        text = re.sub(r"\s+", "", text)
        return [float(text.count(ch)) for ch in _VOCAB]

    def embed_documents(self, texts): return [self._vec(t) for t in texts]
    def embed_query(self, text): return self._vec(text)


FAQS = [
    {"id": "D1", "category": "건강검진", "question": "검진 전 금식은 얼마나 하나요?", "answer": "8시간 금식"},
    {"id": "D2", "category": "건강검진", "question": "수면 내시경 후 운전 되나요?", "answer": "운전 금지"},
    {"id": "D3", "category": "복약안내", "question": "혈압약 공복 복용 되나요?", "answer": "가능"},
]


@pytest.fixture
def temp_index(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "VECTOR_STORE_PATH", str(tmp_path / "idx"))
    return CharBagEmbeddings()


def test_build_creates_index_and_manifest(temp_index, tmp_path):
    import os
    FAQRetriever(FAQS, embeddings=temp_index)
    assert os.path.exists(settings.VECTOR_STORE_PATH)
    assert os.path.exists(os.path.join(settings.VECTOR_STORE_PATH, "data_manifest.json"))


def test_reload_when_data_unchanged(temp_index, capsys):
    FAQRetriever(FAQS, embeddings=temp_index)
    capsys.readouterr()
    FAQRetriever(FAQS, embeddings=temp_index)  # 두 번째: 재로드여야 함
    out = capsys.readouterr().out
    assert "기존 FAISS 인덱스 로드" in out


def test_rebuild_when_data_changed(temp_index, capsys):
    FAQRetriever(FAQS, embeddings=temp_index)
    capsys.readouterr()
    changed = FAQS + [{"id": "D4", "category": "기타", "question": "주차 무료인가요?", "answer": "4시간"}]
    FAQRetriever(changed, embeddings=temp_index)
    out = capsys.readouterr().out
    assert "재빌드" in out


def test_fingerprint_changes_with_content():
    assert _fingerprint(FAQS) != _fingerprint(FAQS + [{"id": "X", "question": "q", "answer": "a"}])


def test_similar_query_is_closer_than_unrelated(temp_index):
    r = FAQRetriever(FAQS, embeddings=temp_index)
    # '금식 검진' 질의는 D1 과 가깝고, 전혀 무관한 질의는 멀어야 함
    near = r.search_with_score("검진 금식 시간", top_k=1)[0][1]
    far = r.search_with_score("주차 보험 청구 예약", top_k=1)[0][1]
    assert near < far


def test_search_with_score_returns_k_tuples(temp_index):
    r = FAQRetriever(FAQS, embeddings=temp_index)
    res = r.search_with_score("혈압약 복용", top_k=2)
    assert len(res) == 2
    assert all(float(score) == float(score) for _, score in res)  # 숫자(float 변환 가능)
    assert res[0][1] <= res[1][1]  # 거리 오름차순
