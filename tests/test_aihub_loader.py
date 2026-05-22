"""AI Hub 로더 파싱 검증 (OpenAI 불필요, 순수 로직)."""
import os

from config import settings
from data.loaders.aihub_loader import AIHubFAQLoader

MOCK_DIR = os.path.join(os.path.dirname(__file__), "sample_aihub")


def _loader():
    return AIHubFAQLoader(MOCK_DIR, settings.AIHUB_FIELD_MAP)


def test_is_available_true_when_json_present():
    assert _loader().is_available() is True


def test_is_available_false_for_empty_dir(tmp_path):
    assert AIHubFAQLoader(str(tmp_path), settings.AIHUB_FIELD_MAP).is_available() is False


def test_korean_keys_and_nested_container_parsed():
    items = _loader().load()
    # MQA-001/002/005 유효 + MQA-003(중복) 제외 + MQA-004(질문 결측) 제외 = 3건
    assert len(items) == 3
    by_id = {it.id: it for it in items}
    assert "MQA-001" in by_id
    assert by_id["MQA-001"].category == "건강검진"
    assert by_id["MQA-001"].question.startswith("위내시경")
    assert by_id["MQA-001"].keywords == ["위내시경", "금연", "검사전주의"]


def test_missing_required_field_is_skipped():
    items = _loader().load()
    assert all(it.id != "MQA-004" for it in items)  # 질문 결측 → 스킵


def test_duplicate_question_deduplicated():
    items = _loader().load()
    questions = [it.question for it in items]
    assert len(questions) == len(set(q.replace(" ", "") for q in questions))


def test_category_defaults_when_absent():
    items = _loader().load()
    mqa5 = next(it for it in items if it.id == "MQA-005")  # 진료과 없음
    assert mqa5.category == "미분류"


def test_source_tag_records_origin():
    items = _loader().load()
    assert all(it.source.startswith("aihub:") for it in items)


def test_top_level_list_schema(tmp_path):
    """최상위가 곧 레코드 배열인 다른 스키마도 처리되는지."""
    import json
    p = tmp_path / "flat.json"
    p.write_text(json.dumps([
        {"id": "F1", "question": "Q1?", "answer": "A1", "category": "기타"},
    ], ensure_ascii=False), encoding="utf-8")
    items = AIHubFAQLoader(str(tmp_path), settings.AIHUB_FIELD_MAP).load()
    assert len(items) == 1 and items[0].id == "F1"
