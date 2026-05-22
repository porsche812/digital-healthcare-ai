"""
전역 설정 계층.

- .env 의 시크릿(OPENAI_API_KEY, AIHUB_* )을 로드합니다.
- LLM / 임베딩 / 검색 파라미터, AI Hub 데이터 경로 및 필드 매핑을 한곳에서 관리합니다.
- 다른 모듈은 이 모듈의 상수만 참조하므로, 동작을 바꾸려면 여기만 고치면 됩니다.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# 1. 시크릿 / 인증
# ---------------------------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# AI Hub 다운로더(aihubshell) 인증값. 데이터 "다운로드 단계"에서만 필요하며,
# 챗봇 런타임에는 사용하지 않습니다. (scripts/download_aihub.sh 참고)
AIHUB_ID = os.getenv("AIHUB_ID")
AIHUB_PW = os.getenv("AIHUB_PW")
AIHUB_API_KEY = os.getenv("AIHUB_API_KEY")


def require_openai_api_key() -> str:
    """OpenAI 키가 없으면 명확한 메시지로 즉시 실패시킵니다(런타임 호출 시점에)."""
    if not OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY 가 설정되지 않았습니다. 프로젝트 루트의 .env 파일에 "
            "OPENAI_API_KEY=sk-... 를 추가해 주세요. (.env.example 참고)"
        )
    return OPENAI_API_KEY


# ---------------------------------------------------------------------------
# 2. LLM / 임베딩 모델
# ---------------------------------------------------------------------------
LLM_MODEL_NAME = "gpt-4o-mini"
LLM_TEMPERATURE = 0.0
EMBEDDING_MODEL_NAME = "text-embedding-3-small"

# ---------------------------------------------------------------------------
# 3. 검색(RAG) 파라미터
# ---------------------------------------------------------------------------
RETRIEVER_TOP_K = 2
# FAISS L2 거리 임계값. 이 값보다 "먼"(=유사하지 않은) 결과는 도메인 밖(OOD)으로 보고 거부합니다.
# 거리이므로 값이 작을수록 유사합니다. 임베딩 모델/데이터에 따라 튜닝이 필요합니다.
RETRIEVER_SCORE_THRESHOLD = 1.5
REWRITE_HISTORY_WINDOW = 4  # 질문 재작성 시 참고할 최근 메시지 수

# ---------------------------------------------------------------------------
# 4. 데이터 소스 설정
# ---------------------------------------------------------------------------
# 데이터 소스 선택: "aihub" | "sample"
#   - aihub : AIHUB_DATA_DIR 의 JSON 을 적재 (없으면 자동으로 sample 폴백)
#   - sample: 저장소에 내장된 데모용 소량 데이터 사용
FAQ_DATA_SOURCE = os.getenv("FAQ_DATA_SOURCE", "aihub")

# aihubshell 로 내려받아 압축 해제한 라벨링데이터(JSON) 들이 위치한 디렉토리.
# 예) ./data/raw/aihub/  아래에 *.json 이 흩어져 있어도 재귀적으로 수집합니다.
AIHUB_DATA_DIR = os.getenv("AIHUB_DATA_DIR", "./data/raw/aihub")

# AI Hub 헬스케어 QA 데이터셋 식별자(다운로드 스크립트에서 사용). 예시 기본값일 뿐이며
# 실제 사용 데이터셋의 dataSetSn 으로 교체하세요. (소개페이지 URL 의 dataSetSn 값)
AIHUB_DATASET_KEY = os.getenv("AIHUB_DATASET_KEY", "")

# AI Hub JSON 의 스키마는 데이터셋/버전마다 다릅니다.
# 아래 매핑은 "후보 키 목록"으로, 레코드에서 먼저 발견되는 키를 사용합니다.
# 본인 데이터셋 스키마에 맞춰 키만 추가/수정하면 로더 코드를 건드릴 필요가 없습니다.
AIHUB_FIELD_MAP = {
    # 레코드 배열이 들어있는 상위 경로 후보 (점 표기 지원). None/빈값이면 최상위가 배열로 간주.
    "records_path": ["data", "documents", "qas", "annotations", "list"],
    "question_keys": ["question", "질문", "Q", "query", "title", "input"],
    "answer_keys": ["answer", "답변", "A", "response", "content", "output"],
    "category_keys": ["category", "진료과", "department", "disease_category", "topic", "subject"],
    "id_keys": ["id", "qa_id", "doc_id", "uid"],
}

# FAISS 인덱스 로컬 저장 경로 (인덱스 + 데이터 지문 manifest 가 함께 저장됨)
VECTOR_STORE_PATH = "./faq_faiss_index"

# ---------------------------------------------------------------------------
# 5. 공통 사용자 메시지
# ---------------------------------------------------------------------------
ERROR_MESSAGE_SYSTEM = "[시스템 오류] 일시적인 통신 문제가 발생했습니다. 잠시 후 다시 시도해 주세요."
ERROR_MESSAGE_INPUT = "[입력 오류] 구체적인 문장으로 질문해 주세요."
ERROR_MESSAGE_INPUT_TOO_LONG = "[입력 오류] 질문이 너무 깁니다. 500자 이하로 작성해 주세요."
ERROR_MESSAGE_NO_MATCH = "[검색 결과 없음] 관련 안내 매뉴얼이 없습니다. 헬스케어 고객센터(1588-0000)로 문의 바람."
ERROR_MESSAGE_OOD = (
    "죄송합니다. 해당 질문은 디지털 헬스케어 FAQ 가이드에 포함되어 있지 않아 "
    "정확한 답변을 드릴 수 없습니다."
)
