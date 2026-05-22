"""
FAQ 데이터의 표준 스키마와 정규화 로직.

데이터 소스(AI Hub / 내장 샘플)가 무엇이든, 애플리케이션 내부에서는 항상
이 FAQItem 형태로 통일됩니다. 덕분에 retriever / service 등 하위 계층은
"데이터가 어디서 왔는지" 신경 쓸 필요가 없습니다.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional


@dataclass
class FAQItem:
    id: str
    category: str
    question: str
    answer: str
    keywords: list[str] = field(default_factory=list)
    difficulty: str = "unknown"
    source: str = "unknown"  # 출처 표기용 ("aihub:파일명", "sample" 등)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _first_present(record: dict, keys: list[str]) -> Optional[Any]:
    """후보 키들을 순서대로 확인하여 처음으로 존재하는 값을 반환."""
    for k in keys:
        if k in record and record[k] not in (None, ""):
            return record[k]
    return None


def normalize_record(
    record: dict,
    field_map: dict,
    index: int,
    source: str,
) -> Optional[FAQItem]:
    """
    원시 레코드(dict) 한 건을 FAQItem 으로 정규화합니다.
    질문 또는 답변이 비어 있으면 None 을 반환하여 호출부에서 건너뛰게 합니다.
    """
    if not isinstance(record, dict):
        return None

    question = _first_present(record, field_map["question_keys"])
    answer = _first_present(record, field_map["answer_keys"])
    if not question or not answer:
        return None  # 필수 필드 누락 → 스킵

    category = _first_present(record, field_map["category_keys"]) or "미분류"
    raw_id = _first_present(record, field_map["id_keys"])
    item_id = str(raw_id) if raw_id is not None else f"{source}-{index:06d}"

    keywords = record.get("keywords") or record.get("키워드") or []
    if isinstance(keywords, str):
        keywords = [keywords]

    return FAQItem(
        id=item_id,
        category=str(category).strip(),
        question=str(question).strip(),
        answer=str(answer).strip(),
        keywords=list(keywords),
        difficulty=str(record.get("difficulty", "unknown")),
        source=source,
    )
