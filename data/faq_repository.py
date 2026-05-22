"""
데이터 접근 계층(Repository)의 공개 API.

이 프로젝트는 'AI Hub 실제 데이터로만' 동작합니다(샘플/폴백 없음).
AI Hub 데이터가 없거나 경로가 틀리면 조용히 넘어가지 않고 즉시 에러를 냅니다.
"""
from __future__ import annotations

import functools

from config import settings
from data.loaders.aihub_loader import AIHubFAQLoader
from data.loaders.aihub_answer_loader import AIHubAnswerFileLoader
from data.schema import FAQItem


def _build_aihub_loader():
    """설정된 형식에 맞는 AI Hub 로더 인스턴스를 생성."""
    if settings.AIHUB_LOADER_FORMAT == "answer_files":
        return AIHubAnswerFileLoader(
            settings.AIHUB_DATA_DIR,
            per_category_limit=settings.AIHUB_PER_CATEGORY_LIMIT,
            total_limit=settings.AIHUB_TOTAL_LIMIT,
            department_filter=settings.AIHUB_DEPARTMENT_FILTER,
            per_disease_limit=settings.AIHUB_PER_DISEASE_LIMIT,
        )
    return AIHubFAQLoader(settings.AIHUB_DATA_DIR, settings.AIHUB_FIELD_MAP)


@functools.lru_cache(maxsize=1)
def _load_items() -> tuple[FAQItem, ...]:
    loader = _build_aihub_loader()
    if not loader.is_available():
        raise RuntimeError(
            f"AI Hub 데이터를 찾을 수 없습니다.\n"
            f"  - AIHUB_DATA_DIR: {settings.AIHUB_DATA_DIR}\n"
            f"  - AIHUB_LOADER_FORMAT: {settings.AIHUB_LOADER_FORMAT}\n"
            f".env 의 AIHUB_DATA_DIR 가 HC-A-*.json 이 들어있는 폴더(또는 상위)를 "
            f"가리키는지 확인하세요. (scripts/download_aihub.sh 로 데이터 취득)"
        )
    items = loader.load()
    print(
        f"✅ FAQ 데이터 로드 완료: {len(items)}개 QA "
        f"(출처: aihub/{settings.AIHUB_LOADER_FORMAT})"
    )
    return tuple(items)


def get_all_faqs() -> list[dict]:
    """애플리케이션 표준 형태(dict 리스트)로 FAQ 를 반환."""
    return [item.to_dict() for item in _load_items()]


def get_faq_items() -> list[FAQItem]:
    """FAQItem 객체가 필요할 때(테스트 등)."""
    return list(_load_items())


def print_data_status() -> None:
    items = _load_items()
    print(f"FAQ 데이터 로드 완료 : {len(items)}개 QA")