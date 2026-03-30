# 🏥 디지털 헬스케어 AI 챗봇 (Digital Healthcare RAG Chatbot)

기존 병원/헬스케어 FAQ 데이터를 바탕으로, FAISS 벡터 기반의 의미 검색과 예외 처리(가드레일) 파이프라인이 탑재된 도메인 특화 멀티턴 AI 챗봇입니다.

## ✨ 주요 기능
- **RAG 기반 의미 검색**: 사용자의 질문과 FAQ 데이터 간의 키워드 및 의미 기반(Semantic) 매칭 알고리즘 (FAISS & OpenAI 임베딩 적용)
- **멀티턴 대화 및 질문 재작성 (Query Rewriting)**: 과거 대화 문맥을 파악하여 짧은 꼬리 질문("술은?", "담배는?")도 완벽한 검색용 질문으로 변환하여 문맥 단절 방지
- **고급 파이프라인(LCEL)**: LLM 답변 생성과 참고 출처(Metadata) 추출을 처리하여 답변 하단에 정확한 출처 표기
- **안전한 가드레일 및 OOD 차단**: 거리 점수(L2 Distance Threshold)를 측정하여 헬스케어 도메인을 벗어난 엉뚱한 질문은 안전하게 답변 거부 (환각 현상 제어)
- **Gradio 웹 UI**: 사용자 친화적인 웹 기반 실시간 채팅 인터페이스 제공

## 🛠 기술 스택
- **Language**: Python 3.11+
- **AI/LLM Framework**: LangChain, OpenAI API (`gpt-4o-mini`, `text-embedding-3-small`)
- **Vector DB**: FAISS (Facebook AI Similarity Search)
- **Frontend**: Gradio

## 📁 프로젝트 아키텍처 (Directory Structure)
본 프로젝트는 **관심사의 분리(Separation of Concerns)** 원칙을 바탕으로, 향후 RAG 고도화 및 시스템 확장에 유연하게 대응할 수 있도록 계층형 아키텍처로 설계되었습니다.

```text
healthcare_chatbot/
├── .venv/                  # 가상환경
├── .env                    # 환경변수 및 시크릿 키 (API Key 등) 보관
├── requirements.txt        # 프로젝트 의존성 패키지 목록
├── README.md               # 프로젝트 개요 및 가이드
│
├── app.py                  # 최상위 실행 진입점 (Entry Point)
│
├── config/                 # 설정 관리 계층
│   └── settings.py         # 전역 설정값 및 환경변수 로드
│
├── data/                   # 데이터 접근 계층 (Repository Layer)
│   └── faq_repository.py   # FAQ 데이터 로드 및 관리 (DB 접근 분리)
│
├── core/                   # AI 코어 및 유틸리티 계층
│   ├── retriever.py        # 데이터 검색 로직 (FAISS Vector DB 연동 및 유사도 검색)
│   ├── prompts.py          # AI 프롬프트 템플릿 통합 관리 (의도 분류, 재작성, RAG)
│   └── llm_builder.py      # LLM 객체 생성 및 LangChain 파이프라인(LCEL) 조립
│
├── service/                # 비즈니스 로직 계층 (Service Layer)
│   └── chat_service.py     # 검증 -> 의도 분류 -> 질문 재작성 -> 검색 -> AI 답변 오케스트레이션
│
├── ui/                     # 프레젠테이션 계층 (View Layer)
│   └── gradio_app.py       # 사용자 인터페이스(Gradio) 화면 구성 및 이벤트 바인딩
│
└── faq_faiss_index/        # (Auto-generated) FAISS 벡터 인덱스 로컬 저장 폴더

## 가상환경 세팅 및 패키지 설치
1. 가상환경 생성 및 활성화, 비활성화
python3 -m venv .venv
source .venv/bin/activate
deactivate

2. 필수 패키지 설치
pip install -r requirements.txt

3. 환경변수 설정
OPENAI_API_KEY = 발급받은 API KEY 입력

4. 애플리케이션 실행
python app.py

