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
RETRIEVER_SCORE_THRESHOLD = float(os.getenv("RETRIEVER_SCORE_THRESHOLD", "0.8"))
REWRITE_HISTORY_WINDOW = 4  # 질문 재작성 시 참고할 최근 메시지 수

# ---------------------------------------------------------------------------
# 4. 데이터 소스 설정 (AI Hub 실데이터 전용)
# ---------------------------------------------------------------------------
# aihubshell 로 내려받아 압축 해제한 라벨링데이터(JSON) 들이 위치한 디렉토리.
# 하위 폴더에 *.json 이 흩어져 있어도 재귀적으로 수집합니다.
AIHUB_DATA_DIR = os.getenv("AIHUB_DATA_DIR", "./data/raw/aihub")

# 다운로드 스크립트에서 사용하는 데이터셋 식별자(dataSetSn).
# 71762 = "초거대 AI 헬스케어 질의응답 데이터"
AIHUB_DATASET_KEY = os.getenv("AIHUB_DATASET_KEY", "71762")

# AI Hub 로더 형식 선택: "answer_files" | "flat"
#   - answer_files : 71762 처럼 답변 파일(HC-A-*.json) 한 건이 한 레코드인 구조.
#                    answer.intro/body/conclusion 을 합쳐 본문으로, department 를 진료과로 사용.
#   - flat         : 한 JSON 안에 question/answer 가 평평하게 들어있는 일반 구조.
AIHUB_LOADER_FORMAT = os.getenv("AIHUB_LOADER_FORMAT", "answer_files")

# [비용 통제] 약 221만 건 전부 임베딩하면 비용/시간이 큽니다.
#   - AIHUB_PER_CATEGORY_LIMIT : 진료과(department)별 최대 적재 건수 (0 = 무제한)
#   - AIHUB_TOTAL_LIMIT        : 전체 최대 적재 건수 (0 = 무제한)
AIHUB_PER_CATEGORY_LIMIT = int(os.getenv("AIHUB_PER_CATEGORY_LIMIT", "150"))
AIHUB_TOTAL_LIMIT = int(os.getenv("AIHUB_TOTAL_LIMIT", "3000"))

# [도메인 집중] 특정 진료과만 적재(부분 문자열 매칭). 예: "내과" → 내과/내분비내과/소화기내과 등.
# 비우면 전체 진료과. 한 과로 좁히면 그 과의 질병 커버리지가 깊어져 답변 적중률이 올라갑니다.
AIHUB_DEPARTMENT_FILTER = os.getenv("AIHUB_DEPARTMENT_FILTER", "") or None
# 한 질병이 인덱스를 독식하지 않도록 질병별 최대 적재 수(다양성 확보). 0 = 무제한.
AIHUB_PER_DISEASE_LIMIT = int(os.getenv("AIHUB_PER_DISEASE_LIMIT", "30"))

# (flat 형식 전용) 스키마 후보 키 매핑. answer_files 형식에서는 사용하지 않습니다.
AIHUB_FIELD_MAP = {
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