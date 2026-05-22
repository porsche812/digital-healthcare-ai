"""로더 공통 인터페이스. 모든 데이터 소스는 load() -> list[FAQItem] 를 구현합니다."""
from __future__ import annotations

from abc import ABC, abstractmethod

from data.schema import FAQItem


class FAQLoader(ABC):
    @abstractmethod
    def load(self) -> list[FAQItem]:
        """데이터 소스를 읽어 정규화된 FAQItem 리스트를 반환합니다."""
        raise NotImplementedError
