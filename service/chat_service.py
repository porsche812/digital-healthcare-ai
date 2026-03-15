from data.faq_repository import get_all_faqs  # FAQ 데이터를 가져오는 저장소 함수 임포트
from core.retriever import FAQRetriever  # 검색 로직 클래스 임포트
from core.llm_builder import get_faq_chain, get_category_chain  # LLM 체인 생성 함수들 임포트
from config import settings  # 전역 설정값 임포트
from langchain_core.messages import HumanMessage, AIMessage

class ChatService:
    """
    사용자 질문 처리하는 핵심 비즈니스 로직임.
    검증 -> 분류 -> 검색 -> 답변 생성 순으로 돌아감.
    """
    def __init__(self):
        # [설계 의도] 객체 생성할 때 필요한 부품들 미리 세팅해둠. 
        # 매번 로드하면 성능 떨어지니까 처음에 한 번만 딱 불러오는 게 효율적임.
        self.faqs = get_all_faqs() 
        self.retriever = FAQRetriever(self.faqs)  
        self.faq_chain = get_faq_chain()
        self.category_chain = get_category_chain()

    def _validate_input(self, question: str):
        """입력값 가드레일 (검증 로직)임"""
        q = question.strip()  # 앞뒤 공백부터 지우기

        if not q:
            return False, settings.ERROR_MESSAGE_INPUT  # 빈 질문 반려
        if len(q) > 500:
            return False, settings.ERROR_MESSAGE_INPUT_TOO_LONG  # 토큰 낭비 방지
        if q.replace(" ", "").isdigit():
            return False, settings.ERROR_MESSAGE_INPUT  # 숫자만 반려
        return True, q
    
    def get_response(self, message, history):
        """
        사용자의 질문을 받아 검증, 검색(RAG), 답변 생성의 전체 사이클을 실행하는 메인 함수
        (Java의 Service/Controller 통합 레이어 역할)
        
        :param message: 사용자가 방금 입력창에 친 질문 (String)
        :param history: Gradio가 전달해주는 이전 대화 기록 (List)
        """
        
        # ---------------------------------------------------------
        # 1. 입력값 검증 (Validation)
        # ---------------------------------------------------------
        # _validate_input 함수를 통해 빈 문자열, 너무 긴 글, 숫자만 있는 글 등을 걸러냅니다.
        # is_valid: 통과 여부 (True/False)
        # validated_q: 양 끝 공백 등이 제거된 깔끔한 문자열 (또는 에러 메시지)
        is_valid, validated_q = self._validate_input(message)

        # 검증을 통과하지 못했다면(False), AI 모델까지 갈 필요 없이 바로 에러 메시지를 화면에 반환합니다.
        if not is_valid: 
            return validated_q 

        try:
            # ---------------------------------------------------------
            # 2. 대화 기록 변환 (Gradio DTO -> LangChain Entity)
            # ---------------------------------------------------------
            # Gradio가 주는 대화 기록 포맷을 LangChain 모델이 이해할 수 있는 Message 객체로 번역합니다.
            chat_history = []
            
            for msg in history:
                # 케이스 A: 최신 Gradio 버전 (딕셔너리 형태 JSON 데이터로 들어올 때)
                # 예: {"role": "user", "content": "안녕하세요"}
                if isinstance(msg, dict):
                    if msg.get("role") == "user":
                        # 사용자의 말은 HumanMessage 객체로 감싸서 리스트에 추가
                        chat_history.append(HumanMessage(content=msg.get("content", "")))
                    elif msg.get("role") == "assistant":
                        # 챗봇의 말은 AIMessage 객체로 감싸서 리스트에 추가
                        chat_history.append(AIMessage(content=msg.get("content", "")))
                
                # 케이스 B: 구버전 Gradio (리스트나 튜플 형태로 들어올 때)
                # 예: ["안녕하세요", "네, 무엇을 도와드릴까요?"]
                elif isinstance(msg, (list, tuple)) and len(msg) == 2:
                    chat_history.append(HumanMessage(content=msg[0])) # 첫 번째는 사용자
                    chat_history.append(AIMessage(content=msg[1]))    # 두 번째는 챗봇

            # ---------------------------------------------------------
            # 3. 데이터 검색 (RAG - Retriever)
            # ---------------------------------------------------------
            # 사용자의 질문(validated_q)과 가장 유사한 FAQ 데이터를 저장소에서 2개(top_k) 찾아옵니다.
            matched_docs = self.retriever.search(validated_q, top_k=2)

            # 만약 DB(또는 리스트)에 관련 있는 내용이 전혀 없다면, 
            # 엉뚱한 대답을 방지하기 위해 정해둔 "검색 결과 없음" 메시지를 바로 반환합니다.
            if not matched_docs:
                return settings.ERROR_MESSAGE_NO_MATCH
            
            # ---------------------------------------------------------
            # 4. 프롬프트 문맥(Context) 조립
            # ---------------------------------------------------------
            # 검색해 온 딕셔너리 리스트를 AI가 읽기 편하게 하나의 긴 문자열(String)로 합칩니다.
            # \n (줄바꿈)을 기준으로 질문과 답변을 이어 붙입니다.
            context_text = "\n".join([f"사용자: {d['question']}\nAI 챗봇: {d['answer']}" for d in matched_docs])

            # ---------------------------------------------------------
            # 5. LLM 체인 실행 및 답변 생성 (Invoke)
            # ---------------------------------------------------------
            # 미리 만들어둔 LangChain(faq_chain)에 준비된 재료들을 맵(Map/Dict) 형태로 주입합니다.
            # 이 재료들은 prompts.py에 있는 대본(Template)의 {변수명} 자리에 쏙쏙 들어갑니다.
            response = self.faq_chain.invoke({
                "context": context_text,   # 검색해 온 FAQ 참고 자료
                "question": validated_q,   # 사용자의 현재 질문
                "history": chat_history    # 방금 위에서 변환한 과거 대화 기록 (이걸로 문맥 유지!)
            })

            # 모델이 생성하고 파서(StrOutputParser)가 문자열로 예쁘게 다듬은 최종 답변을 반환합니다.
            return response
        
        # ---------------------------------------------------------
        # 6. 예외 처리 (Exception Handling)
        # ---------------------------------------------------------
        # 위 과정 중(API 통신 에러 등) 예상치 못한 에러가 터지면 시스템 다운을 막고 여기로 빠집니다.
        except Exception as e:
            # 개발자 확인용 로그 출력
            print(f"Error : {e}")
            # 사용자에게 보여줄 안전한 범용 에러 메시지 반환
            return settings.ERROR_MESSAGE_SYSTEM