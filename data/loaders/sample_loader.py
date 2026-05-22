"""내장 데모 데이터 로더(폴백)."""
from __future__ import annotations

from data.loaders.base import FAQLoader
from data.schema import FAQItem
from data.sample_faqs import SAMPLE_FAQS


class SampleFAQLoader(FAQLoader):
    def load(self) -> list[FAQItem]:
        return [
            FAQItem(
                id=r["id"],
                category=r["category"],
                question=r["question"],
                answer=r["answer"],
                keywords=list(r.get("keywords", [])),
                difficulty=r.get("difficulty", "unknown"),
                source="sample",
            )
            for r in SAMPLE_FAQS
        ]
