from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser # AI의 응답 객체에서 텍스트만 추출하는 파서 임포트
from config import settings # 앞서 작성한 API 키와 모델 설정값(settings.py) 가져오기
from .prompts import FAQ_CHAT_PROMPT, CATEGORY_CLASSIFIER_PROMPT # 관리 중인 프롬프트 템플릿 가져오기

def get_llm():
    """
    설정값에 기반하여 OpenAI LLM 객체를 생성합니다.
    (자바의 모델 생성 메서드나 Bean 정의와 비슷합니다.)
    """
    return ChatOpenAI(
        openai_api_key=settings.OPENAI_API_KEY,
        model=settings.LLM_MODEL_NAME,
        temperature=settings.LLM_TEMPERATURE, # 답변의 창의성 정도 (0이면 가장 일관적임)
    )

def get_faq_chain():
    """
    FAQ 답변 생성을 위한 LCEL 체인을 조립하여 반환합니다.
    구조: 프롬프트 입력 -> LLM 연산 -> 문자열 추출
    """
    llm = get_llm() # 모델 인스턴스 생성
    output_parser = StrOutputParser() # 파서 인스턴스 생성

    # '|' (파이프) 연산자를 통해 각 컴포넌트를 체인처럼 연결합니다 (LangChain Expression Language).
    # 1. 사용자의 질문을 프롬프트에 끼워 넣고,
    # 2. 모델에 던져서 연산한 뒤,
    # 3. 결과물에서 군더더기를 떼고 텍스트만 딱 뽑아내는 파이프라인입니다.
    return FAQ_CHAT_PROMPT | llm | output_parser

def get_category_chain():
    """
    사용자 질문의 카테고리를 분류하기 위한 전용 체인을 조립합니다.
    """
    llm = get_llm() # 모델 인스턴스 생성
    output_parser = StrOutputParser() # 파서 인스턴스 생성

    # 카테고리 분류 전용 프롬프트를 사용하여 위와 동일한 구조로 체인을 만듭니다.
    return CATEGORY_CLASSIFIER_PROMPT | llm | output_parser

