"""
데이터 접근 계층(Repository)의 공개 API.

서비스/리트리버는 get_all_faqs() 만 호출하면 되며, 내부적으로 설정에 따라
AI Hub 로더 또는 샘플 로더를 선택합니다. AI Hub 데이터가 없으면 안전하게
샘플 데이터로 폴백합니다(앱이 죽지 않도록).
"""
from __future__ import annotations

import functools

from config import settings
from data.loaders.aihub_loader import AIHubFAQLoader
from data.loaders.sample_loader import SampleFAQLoader
from data.sample_faqs import SAMPLE_TEST_QUERIES
from data.schema import FAQItem


def _build_loader():
    if settings.FAQ_DATA_SOURCE == "sample":
        return SampleFAQLoader(), "sample(명시적 설정)"

    # 기본값: aihub. 단, 실제 데이터가 없으면 sample 로 폴백.
    aihub = AIHubFAQLoader(settings.AIHUB_DATA_DIR, settings.AIHUB_FIELD_MAP)
    if aihub.is_available():
        return aihub, f"aihub({settings.AIHUB_DATA_DIR})"
    print(
        f"⚠️  AI Hub 데이터({settings.AIHUB_DATA_DIR})가 없어 내장 샘플로 폴백합니다. "
        f"실제 데이터는 scripts/download_aihub.sh 참고."
    )
    return SampleFAQLoader(), "sample(폴백)"


@functools.lru_cache(maxsize=1)
def _load_items() -> tuple[FAQItem, ...]:
    loader, origin = _build_loader()
    items = loader.load()
    print(f"✅ FAQ 데이터 로드 완료: {len(items)}개 QA (출처: {origin})")
    return tuple(items)


def get_all_faqs() -> list[dict]:
    """애플리케이션 표준 형태(dict 리스트)로 FAQ 를 반환."""
    return [item.to_dict() for item in _load_items()]


def get_faq_items() -> list[FAQItem]:
    """FAQItem 객체가 필요할 때(테스트 등)."""
    return list(_load_items())


def get_test_queries() -> list[dict]:
    """회귀 테스트용 질의 세트. (현재는 샘플 기준)"""
    return list(SAMPLE_TEST_QUERIES)


def print_data_status() -> None:
    items = _load_items()
    print(f"FAQ 데이터 로드 완료 : {len(items)}개 QA, {len(SAMPLE_TEST_QUERIES)}개 테스트 질의")
