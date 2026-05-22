"""
AI Hub 공공 의료 QA 데이터 로더.

[중요 - AI Hub 데이터 취득 방식]
AI Hub(aihub.or.kr) 데이터는 실행 중에 호출하는 실시간 REST 조회 API 가 아니라,
(1) 로그인 → (2) 데이터셋 다운로드 '승인' → (3) aihubshell 로 분할압축(zip) 다운로드 →
(4) 병합 후 압축 해제 의 오프라인 절차로 취득합니다. 특히 보건의료 데이터는 '안심존'을
통해 개방되는 경우가 많아 더 엄격합니다.

따라서 본 로더는 "이미 내려받아 압축 해제된 라벨링데이터(JSON)"가 들어있는
디렉토리(settings.AIHUB_DATA_DIR)를 재귀적으로 읽어 정규화하는 역할을 합니다.
다운로드 자동화는 scripts/download_aihub.sh 를 참고하세요.

AI Hub JSON 스키마는 데이터셋/버전마다 제각각이므로, 필드 매핑은
settings.AIHUB_FIELD_MAP 으로 외부화했습니다. 본인 데이터셋에 맞춰 키만 바꾸면 됩니다.
"""
from __future__ import annotations

import glob
import json
import os
from typing import Any

from data.loaders.base import FAQLoader
from data.schema import FAQItem, normalize_record


class AIHubFAQLoader(FAQLoader):
    def __init__(self, data_dir: str, field_map: dict):
        self.data_dir = data_dir
        self.field_map = field_map

    # -- public ------------------------------------------------------------
    def is_available(self) -> bool:
        """디렉토리가 존재하고 JSON 이 1개라도 있으면 True."""
        return bool(self._json_files())

    def load(self) -> list[FAQItem]:
        files = self._json_files()
        if not files:
            raise FileNotFoundError(
                f"AI Hub 데이터를 찾을 수 없습니다: '{self.data_dir}'. "
                f"aihubshell 로 데이터를 받아 압축 해제한 뒤 해당 경로에 두거나, "
                f".env 의 FAQ_DATA_SOURCE=sample 로 전환하세요."
            )

        items: list[FAQItem] = []
        seen_questions: set[str] = set()

        for path in files:
            source = f"aihub:{os.path.basename(path)}"
            for idx, record in enumerate(self._iter_records(path)):
                item = normalize_record(record, self.field_map, idx, source)
                if item is None:
                    continue
                # 동일 질문 중복 제거(여러 파일에 같은 QA 가 반복되는 경우 방지)
                dedup_key = item.question.replace(" ", "")
                if dedup_key in seen_questions:
                    continue
                seen_questions.add(dedup_key)
                items.append(item)

        if not items:
            raise ValueError(
                "AI Hub JSON 을 읽었으나 유효한 QA 레코드를 추출하지 못했습니다. "
                "settings.AIHUB_FIELD_MAP 의 question_keys/answer_keys 가 "
                "실제 스키마와 맞는지 확인하세요."
            )
        return items

    # -- internals ---------------------------------------------------------
    def _json_files(self) -> list[str]:
        if not os.path.isdir(self.data_dir):
            return []
        return sorted(glob.glob(os.path.join(self.data_dir, "**", "*.json"), recursive=True))

    def _iter_records(self, path: str):
        """파일 하나에서 레코드(dict)들을 순회 yield. 다양한 컨테이너 형태를 지원."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"⚠️  AI Hub JSON 파싱 실패(건너뜀): {path} ({e})")
            return

        records = self._extract_records(payload)
        for rec in records:
            yield rec

    def _extract_records(self, payload: Any) -> list[dict]:
        # 1) 최상위가 곧 레코드 배열
        if isinstance(payload, list):
            return [r for r in payload if isinstance(r, dict)]

        if isinstance(payload, dict):
            # 2) 설정된 후보 경로에서 배열 탐색 (점 표기 중첩 지원)
            for path_key in self.field_map.get("records_path", []):
                node = self._dig(payload, path_key)
                if isinstance(node, list) and node:
                    return [r for r in node if isinstance(r, dict)]
            # 3) 후보 경로가 없으면, dict 값 중 첫 번째 dict-list 를 자동 탐색
            for v in payload.values():
                if isinstance(v, list) and v and isinstance(v[0], dict):
                    return v
            # 4) 단일 레코드 파일
            return [payload]
        return []

    @staticmethod
    def _dig(payload: dict, dotted: str) -> Any:
        node: Any = payload
        for part in dotted.split("."):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                return None
        return node
