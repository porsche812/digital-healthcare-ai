import os
from dotenv import load_dotenv

# .env 파일에 기록된 환경변수를 로드
load_dotenv()

# OpenAI API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# LLM 관련 전역 설정
LLM_MODEL_NAME = "gpt-4o-mini" # 사용할 OpenAI 모델 이름
LLM_TEMPERATURE = 0.0 # 답변의 창의성 정도

# 프로젝트 전역에서 사용할 공통 메시지
ERROR_MESSAGE_SYSTEM = "[시스템 오류] 일시적인 통신 문제가 발생했습니다. 잠시 후 다시 시도해 주세요."
ERROR_MESSAGE_INPUT = "[입력 오류] 구체적인 문장으로 질문해 주세요."
ERROR_MESSAGE_INPUT_TOO_LONG = "[입력 오류] 질문이 너무 깁니다. 500자 이하로 작성해 주세요."
ERROR_MESSAGE_NO_MATCH = "[검색 결과 없음] 관련 안내 매뉴얼이 없습니다. 헬스케어 고객센터(1588-0000)로 문의 바람."