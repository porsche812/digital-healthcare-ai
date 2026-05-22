"""
FAISS 기반 검색기.

기존 코드의 버그였던 "데이터가 바뀌어도 디스크의 옛 인덱스를 그대로 로드"하는 문제를
data fingerprint(manifest) 비교로 해결합니다. 데이터 내용/개수가 바뀌면 자동 재빌드합니다.

또한 OpenAIEmbeddings 를 외부에서 주입할 수 있어(테스트 시 FakeEmbeddings 사용 가능)
OpenAI 키 없이도 검색 파이프라인을 검증할 수 있습니다.
"""
from __future__ import annotations

import hashlib
import json
import os

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from config import settings

_MANIFEST_NAME = "data_manifest.json"


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
    def __init__(self, faq_data: list[dict], embeddings: Embeddings | None = None):
        self.embeddings = embeddings or _build_embeddings()
        self.fingerprint = _fingerprint(faq_data)
        self.vectorstore = self._load_or_build(faq_data)

    # -- index lifecycle ---------------------------------------------------
    def _manifest_path(self) -> str:
        return os.path.join(settings.VECTOR_STORE_PATH, _MANIFEST_NAME)

    def _index_is_fresh(self) -> bool:
        """디스크 인덱스가 존재하고, 저장 당시 데이터 지문이 현재와 같으면 True."""
        if not os.path.exists(settings.VECTOR_STORE_PATH):
            return False
        try:
            with open(self._manifest_path(), "r", encoding="utf-8") as f:
                saved = json.load(f).get("fingerprint")
            return saved == self.fingerprint
        except (OSError, json.JSONDecodeError):
            return False

    def _load_or_build(self, faq_data: list[dict]) -> FAISS:
        if self._index_is_fresh():
            print("📦 기존 FAISS 인덱스 로드 (데이터 변경 없음)")
            return FAISS.load_local(
                settings.VECTOR_STORE_PATH,
                self.embeddings,
                allow_dangerous_deserialization=True,  # 로컬 자체 생성 파일이므로 허용
            )

        print("🛠️  데이터 변경 감지 또는 인덱스 없음 → FAISS 인덱스 재빌드")
        documents = [
            Document(
                page_content=f"Q: {item['question']}\nA: {item['answer']}",
                metadata={"id": item["id"], "category": item["category"]},
            )
            for item in faq_data
        ]
        vectorstore = FAISS.from_documents(documents, self.embeddings)
        vectorstore.save_local(settings.VECTOR_STORE_PATH)
        with open(self._manifest_path(), "w", encoding="utf-8") as f:
            json.dump({"fingerprint": self.fingerprint, "count": len(faq_data)}, f)
        return vectorstore

    # -- search API --------------------------------------------------------
    def search(self, query: str, top_k: int = settings.RETRIEVER_TOP_K) -> list[Document]:
        return self.vectorstore.similarity_search(query, k=top_k)

    def search_with_score(
        self, query: str, top_k: int = settings.RETRIEVER_TOP_K
    ) -> list[tuple[Document, float]]:
        """(문서, L2거리) 튜플 리스트. 거리가 작을수록 유사합니다."""
        return self.vectorstore.similarity_search_with_score(query, k=top_k)
