"""입력 검증(_validate_input) 가드레일 테스트.

ChatService.__init__ 은 OpenAI 를 요구하므로, 검증 로직만 떼어 함수처럼 호출한다.
(_validate_input 은 self 를 쓰지 않는 사실상 순수 함수)
"""
from config import settings
from service.chat_service import ChatService


def _validate(text):
    # 인스턴스 생성 없이 언바운드 메서드를 임의 객체로 호출
    return ChatService._validate_input(object(), text)


def test_empty_input_rejected():
    ok, msg = _validate("   ")
    assert ok is False and msg == settings.ERROR_MESSAGE_INPUT


def test_none_input_rejected():
    ok, msg = _validate(None)
    assert ok is False and msg == settings.ERROR_MESSAGE_INPUT


def test_too_long_input_rejected():
    ok, msg = _validate("가" * 501)
    assert ok is False and msg == settings.ERROR_MESSAGE_INPUT_TOO_LONG


def test_digits_only_rejected():
    ok, msg = _validate("12345 678")
    assert ok is False and msg == settings.ERROR_MESSAGE_INPUT


def test_normal_question_passes():
    ok, q = _validate("  검진 전 금식 시간 알려줘  ")
    assert ok is True and q == "검진 전 금식 시간 알려줘"
