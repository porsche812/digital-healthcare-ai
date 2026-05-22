"""
'초거대 AI 헬스케어 질의응답 데이터'(AI Hub dataSetSn=71762) 전용 로더.

이 데이터셋은 질문/답변이 별도 폴더로 분리되어 있고, 둘을 잇는 공통 ID가 없습니다.
대신 답변 파일(HC-A-*.json) 한 건이 "질병 + 질문유형(intention) + 진료과 + 상세 답변"을
모두 담고 있어, RAG 검색에는 답변 파일만으로 충분합니다.

구조 예:
  2.답변/{disease_category}/{disease_name}/{intention}/HC-A-*.json
  {
    "disease_name": {"kor": "위염", ...},
    "department": ["내과", "소화기내과"],
    "intention": "치료",
    "answer": {"intro": "...", "body": "...", "conclusion": "..."}
  }

[설계 결정]
- 데이터가 약 221만 건으로 방대해, 전부 임베딩하면 비용/시간이 큽니다.
- 도메인을 한 진료과(예: 내과)로 좁히면 (1) 임베딩 비용을 통제하면서 (2) 해당 과의
  질병 커버리지를 깊게 확보해 "물어보면 대체로 답하는" 밀도 높은 챗봇이 됩니다.
- department_filter 로 특정 진료과만 적재하고, per_disease_limit 로 한 질병이 인덱스를
  독식하지 않게 하여 질병 다양성을 보장합니다.
"""
from __future__ import annotations

import json
import os
from collections import defaultdict

from data.loaders.base import FAQLoader
from data.schema import FAQItem


class AIHubAnswerFileLoader(FAQLoader):
    def __init__(
        self,
        data_dir: str,
        per_category_limit: int = 150,
        total_limit: int = 3000,
        department_filter: str | None = None,
        per_disease_limit: int = 0,
    ):
        self.data_dir = data_dir
        self.per_category_limit = per_category_limit  # 0 = 무제한
        self.total_limit = total_limit                # 0 = 무제한
        # 이 진료과만 적재(부분 문자열 매칭: "내과" → 내과/내분비내과/소화기내과 등). None=전체
        self.department_filter = department_filter
        self.per_disease_limit = per_disease_limit    # 질병별 최대 적재 수(다양성 확보), 0 = 무제한

    # -- public ------------------------------------------------------------
    def is_available(self) -> bool:
        return self._has_any_answer_file()

    def load(self) -> list[FAQItem]:
        all_paths = self._answer_files()
        if not all_paths:
            raise FileNotFoundError(
                f"AI Hub 답변 파일(HC-A-*.json)을 찾을 수 없습니다: '{self.data_dir}'. "
                f"경로가 '2.답변' 폴더를 포함하는지 확인하세요."
            )

        candidates = self._stride_sample(all_paths)

        per_cat: dict[str, int] = defaultdict(int)
        per_disease: dict[str, int] = defaultdict(int)
        items: list[FAQItem] = []

        for path in candidates:
            if self.total_limit and len(items) >= self.total_limit:
                break
            record = self._read_json(path)
            if record is None:
                continue

            departments = record.get("department") or []
            # 진료과 필터(부분 문자열 매칭)
            if self.department_filter and not any(self.department_filter in d for d in departments):
                continue

            item = self._to_item(record, path)
            if item is None:
                continue

            disease = (record.get("disease_name") or {}).get("kor", "").strip() or "미상"
            if self.per_disease_limit and per_disease[disease] >= self.per_disease_limit:
                continue
            if self.per_category_limit and per_cat[item.category] >= self.per_category_limit:
                continue

            per_disease[disease] += 1
            per_cat[item.category] += 1
            items.append(item)

        if not items:
            raise ValueError(
                "조건에 맞는 유효한 레코드를 추출하지 못했습니다. "
                f"(department_filter={self.department_filter}) 필터/경로를 확인하세요."
            )

        scope = f"진료과='{self.department_filter}'" if self.department_filter else f"진료과 {len(per_cat)}종"
        print(
            f"   ↳ 전체 {len(all_paths):,}개 중 {scope} 에서 질병 {len(per_disease)}종 {len(items):,}건 적재 "
            f"(질병당 최대 {self.per_disease_limit or '∞'}, 전체 최대 {self.total_limit or '∞'})"
        )
        return items

    def _stride_sample(self, paths: list[str]) -> list[str]:
        """전체 목록에서 일정 간격으로 뽑아 데이터 전반을 고르게 커버한다.
        진료과 필터가 있으면 매칭률이 낮으므로 후보를 더 넉넉히 잡는다."""
        if not self.total_limit:
            return paths
        multiplier = 15 if self.department_filter else 5
        budget = self.total_limit * multiplier
        if len(paths) <= budget:
            return paths
        step = len(paths) // budget
        return paths[::step][:budget]

    # -- internals ---------------------------------------------------------
    def _answer_files(self) -> list[str]:
        if not os.path.isdir(self.data_dir):
            return []
        found: list[str] = []
        for root, _dirs, files in os.walk(self.data_dir):
            if "2.답변" not in root:
                continue
            for fn in files:
                if fn.startswith("HC-A-") and fn.endswith(".json"):
                    found.append(os.path.join(root, fn))
        if not found:
            for root, _dirs, files in os.walk(self.data_dir):
                for fn in files:
                    if fn.startswith("HC-A-") and fn.endswith(".json"):
                        found.append(os.path.join(root, fn))
        return sorted(found)

    def _has_any_answer_file(self) -> bool:
        for root, _dirs, files in os.walk(self.data_dir):
            for fn in files:
                if fn.startswith("HC-A-") and fn.endswith(".json"):
                    return True
        return False

    @staticmethod
    def _read_json(path: str):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    @staticmethod
    def _to_item(record: dict, path: str) -> FAQItem | None:
        if not isinstance(record, dict):
            return None

        ans = record.get("answer") or {}
        body = " ".join(
            part for part in (ans.get("intro"), ans.get("body"), ans.get("conclusion"))
            if part
        ).strip()
        if not body:
            return None

        disease = (record.get("disease_name") or {}).get("kor", "").strip()
        intention = (record.get("intention") or "").strip()
        pseudo_q = f"{disease} {intention}".strip() or disease or "건강 정보"

        departments = record.get("department") or []
        category = departments[0] if departments else (record.get("disease_category") or "미분류")
        fid = record.get("fileName") or os.path.splitext(os.path.basename(path))[0]

        return FAQItem(
            id=str(fid),
            category=str(category).strip(),
            question=pseudo_q,
            answer=body,
            keywords=[d for d in departments] + ([disease] if disease else []),
            difficulty=intention or "unknown",
            source=f"aihub71762:{os.path.basename(path)}",
        )
