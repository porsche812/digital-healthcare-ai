"""
FAISS 인덱스 오프라인 사전 빌드 스크립트.

서버 기동 시점이 아니라 미리 인덱스를 만들어 두고 싶을 때 실행합니다.
데이터가 바뀌면 retriever 가 지문(fingerprint) 불일치를 감지해 자동 재빌드하지만,
이 스크립트로 명시적으로 미리 빌드해 두면 첫 응답 지연을 없앨 수 있습니다.

    python scripts/build_index.py

(프로젝트 루트에서 실행해야 import 경로가 맞습니다.)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.retriever import FAQRetriever  # noqa: E402
from data.faq_repository import get_all_faqs, print_data_status  # noqa: E402


def main():
    print_data_status()
    faqs = get_all_faqs()
    FAQRetriever(faqs)  # 생성 과정에서 인덱스 빌드/저장이 일어남
    print("✅ FAISS 인덱스 빌드/저장 완료")


if __name__ == "__main__":
    main()
