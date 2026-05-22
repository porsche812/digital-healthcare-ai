"""
FAISS 기반 검색기 (langchain-community 의존성 없음).

langchain-community 의 FAISS 래퍼는 구버전 langchain-core(<1.0)를 요구해서, 현재
환경의 langchain-core 1.x 와 충돌합니다. 그래서 community 를 거치지 않고 faiss 를
직접 사용합니다(IndexFlatL2). 문서 본문/메타데이터는 docstore.json 에 함께 저장합니다.

- 데이터가 바뀌면 지문(fingerprint) 비교로 자동 재빌드합니다.
- 임베딩을 외부에서 주입 가능(테스트 시 가짜 임베딩 사용) → OpenAI 키 없이 검증 가능.

저장 구조 (VECTOR_STORE_PATH 디렉토리):
  index.faiss          # faiss 인덱스
  docstore.json        # [{page_content, metadata}, ...] (인덱스 순서와 1:1)
  data_manifest.json   # {"fingerprint": ..., "count": ...}
"""
from __future__ import annotations

import hashlib
import json
import os

import faiss
import numpy as np
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from config import settings

_MANIFEST_NAME = "data_manifest.json"
_INDEX_NAME = "index.faiss"
_DOCSTORE_NAME = "docstore.json"


def _fingerprint(faq_data: list[dict]) -> str:
    """FAQ 데이터의 내용 지문(해시). 한 글자라도 바뀌면 값이 달라집니다."""
    payload = json.dumps(
        [(d.get("id"), d.get("question"), d.get("answer")) for d in faq_data],
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _build_embeddings() -> Embeddings:
    from langchain_openai import OpenAIEmbeddings  # 지연 임포트(테스트 시 OpenAI 불필요)

    return OpenAIEmbeddings(
        openai_api_key=settings.require_openai_api_key(),
        model=settings.EMBEDDING_MODEL_NAME,
    )


class FAQRetriever:
    def __init__(self, faq_data, embeddings=None):
        self.embeddings = embeddings or _build_embeddings()
        self.fingerprint = _fingerprint(faq_data)
        self._index = None
        self._docs = []
        self._load_or_build(faq_data)

    # -- paths -------------------------------------------------------------
    def _p(self, name: str) -> str:
        return os.path.join(settings.VECTOR_STORE_PATH, name)

    def _index_is_fresh(self) -> bool:
        if not os.path.isdir(settings.VECTOR_STORE_PATH):
            return False
        if not (os.path.exists(self._p(_INDEX_NAME)) and os.path.exists(self._p(_DOCSTORE_NAME))):
            return False
        try:
            with open(self._p(_MANIFEST_NAME), "r", encoding="utf-8") as f:
                return json.load(f).get("fingerprint") == self.fingerprint
        except (OSError, json.JSONDecodeError):
            return False

    # -- lifecycle ---------------------------------------------------------
    def _load_or_build(self, faq_data) -> None:
        if self._index_is_fresh():
            print("기존 FAISS 인덱스 로드 (데이터 변경 없음)")
            self._index = faiss.read_index(self._p(_INDEX_NAME))
            with open(self._p(_DOCSTORE_NAME), "r", encoding="utf-8") as f:
                raw = json.load(f)
            self._docs = [Document(page_content=d["page_content"], metadata=d["metadata"]) for d in raw]
            return

        print("데이터 변경 감지 또는 인덱스 없음 -> FAISS 인덱스 재빌드")
        self._docs = [
            Document(
                page_content=f"Q: {item['question']}\nA: {item['answer']}",
                metadata={"id": item["id"], "category": item["category"]},
            )
            for item in faq_data
        ]
        texts = [d.page_content for d in self._docs]
        vectors = np.array(self.embeddings.embed_documents(texts), dtype="float32")

        index = faiss.IndexFlatL2(vectors.shape[1])
        index.add(vectors)
        self._index = index

        os.makedirs(settings.VECTOR_STORE_PATH, exist_ok=True)
        faiss.write_index(index, self._p(_INDEX_NAME))
        with open(self._p(_DOCSTORE_NAME), "w", encoding="utf-8") as f:
            json.dump(
                [{"page_content": d.page_content, "metadata": d.metadata} for d in self._docs],
                f, ensure_ascii=False,
            )
        with open(self._p(_MANIFEST_NAME), "w", encoding="utf-8") as f:
            json.dump({"fingerprint": self.fingerprint, "count": len(faq_data)}, f)

    # -- search API --------------------------------------------------------
    def search_with_score(self, query: str, top_k: int = settings.RETRIEVER_TOP_K):
        """(문서, L2거리) 튜플 리스트. 거리가 작을수록 유사합니다."""
        if self._index is None or not self._docs:
            return []
        q = np.array([self.embeddings.embed_query(query)], dtype="float32")
        k = min(top_k, len(self._docs))
        distances, indices = self._index.search(q, k)
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0:
                continue
            results.append((self._docs[idx], float(dist)))
        return results

    def search(self, query: str, top_k: int = settings.RETRIEVER_TOP_K):
        return [doc for doc, _ in self.search_with_score(query, top_k)]
