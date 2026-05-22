"""AIHubAnswerFileLoader (dataSetSn=71762 전용) 테스트."""
import json
import os

from data.loaders.aihub_answer_loader import AIHubAnswerFileLoader


def _write(base, disease_cat, disease, intention, fid, answer, department):
    d = os.path.join(base, "2.답변", disease_cat, disease, intention)
    os.makedirs(d, exist_ok=True)
    rec = {
        "fileName": fid,
        "disease_category": disease_cat,
        "disease_name": {"kor": disease, "eng": "x"},
        "department": department,
        "intention": intention,
        "answer": answer,
    }
    with open(os.path.join(d, f"{fid}.json"), "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False)


def test_parses_and_merges_answer(tmp_path):
    _write(tmp_path, "피부질환", "섬유종", "증상", "HC-A-1",
           {"intro": "인트로.", "body": "본문.", "conclusion": "결론."}, ["피부과"])
    items = AIHubAnswerFileLoader(str(tmp_path)).load()
    assert len(items) == 1
    it = items[0]
    assert it.answer == "인트로. 본문. 결론."   # 세 조각 병합
    assert it.question == "섬유종 증상"          # 질병 + intention
    assert it.category == "피부과"               # department[0]
    assert it.id == "HC-A-1"


def test_empty_answer_skipped(tmp_path):
    _write(tmp_path, "기타", "감기", "치료", "HC-A-empty",
           {"intro": "", "body": "", "conclusion": ""}, ["내과"])
    items = AIHubAnswerFileLoader(str(tmp_path)).load() if False else None
    # 유효 레코드가 0이면 ValueError 가 나야 하므로 별도 검증
    import pytest
    with pytest.raises(ValueError):
        AIHubAnswerFileLoader(str(tmp_path)).load()


def test_partial_answer_joined(tmp_path):
    _write(tmp_path, "소화기", "위염", "치료", "HC-A-2",
           {"intro": "원인에 따라 다릅니다.", "body": "", "conclusion": "내시경 권장."}, ["내과"])
    items = AIHubAnswerFileLoader(str(tmp_path)).load()
    assert items[0].answer == "원인에 따라 다릅니다. 내시경 권장."  # 빈 body 는 건너뜀


def test_category_falls_back_to_disease_category(tmp_path):
    _write(tmp_path, "기타", "대사증후군", "검진", "HC-A-3",
           {"intro": "검진 안내.", "body": "", "conclusion": ""}, [])  # department 없음
    items = AIHubAnswerFileLoader(str(tmp_path)).load()
    assert items[0].category == "기타"  # disease_category 로 폴백


def test_per_category_limit(tmp_path):
    for i in range(10):
        _write(tmp_path, "피부질환", f"질병{i}", "증상", f"HC-A-D{i}",
               {"intro": f"내용{i}", "body": "", "conclusion": ""}, ["피부과"])
    items = AIHubAnswerFileLoader(str(tmp_path), per_category_limit=3, total_limit=0).load()
    assert len(items) == 3  # 같은 진료과(피부과) 상한 3


def test_total_limit(tmp_path):
    for i in range(10):
        _write(tmp_path, "기타", f"질병{i}", "증상", f"HC-A-T{i}",
               {"intro": f"내용{i}", "body": "", "conclusion": ""}, [f"과{i}"])
    items = AIHubAnswerFileLoader(str(tmp_path), per_category_limit=0, total_limit=4).load()
    assert len(items) == 4  # 전체 상한 4


def test_is_available(tmp_path):
    assert AIHubAnswerFileLoader(str(tmp_path)).is_available() is False
    _write(tmp_path, "기타", "감기", "치료", "HC-A-9",
           {"intro": "내용", "body": "", "conclusion": ""}, ["내과"])
    assert AIHubAnswerFileLoader(str(tmp_path)).is_available() is True
