# 🏥 디지털 헬스케어 AI 챗봇 (Digital Healthcare RAG Chatbot)

AI Hub 공공 의료 QA 데이터를 적재하여, FAISS 벡터 기반 의미 검색과 예외 처리(가드레일)
파이프라인을 갖춘 도메인 특화 멀티턴 AI 챗봇입니다. 데이터 적재 → 인덱싱 → 검색 → 생성의
각 단계가 계층으로 분리되어 있어 데이터 소스 교체와 RAG 고도화가 쉽습니다.

## ✨ 주요 기능
- **AI Hub 공공 의료 데이터 적재**: 하드코딩 데이터를 제거하고, AI Hub에서 내려받은
  의료 QA JSON을 정규화·중복제거하여 적재하는 **로더 계층**으로 대체. 데이터가 없으면
  내장 데모 샘플로 자동 폴백합니다.
- **RAG 의미 검색 (OpenAI Embeddings + FAISS)**: `text-embedding-3-small` 임베딩과
  FAISS 벡터스토어로 의미 기반 검색을 수행합니다.
- **데이터 변경 자동 감지 & 인덱스 재빌드**: 데이터 지문(fingerprint)을 인덱스와 함께
  저장하여, 데이터가 바뀌면 옛 인덱스를 그대로 쓰지 않고 자동 재빌드합니다.
- **멀티턴 + 질문 재작성 (Query Rewriting)**: 직전 대화 문맥을 반영해 짧은 꼬리 질문
  ("그럼 물은?")을 검색용 완전 문장으로 변환합니다.
- **LCEL + RunnableParallel 파이프라인**: 답변 생성과 출처(메타데이터) 표기를 병렬
  실행한 뒤 병합하여 답변 하단에 참고 문서를 명시합니다.
- **가드레일 & OOD 차단**: 입력 검증 + L2 거리 임계값으로 도메인 밖 질문을 안전하게 거부합니다.
- **Gradio 웹 UI**: 실시간 채팅 인터페이스.

## 🛠 기술 스택
- **Language**: Python 3.11+
- **AI/LLM**: LangChain (LCEL, RunnableParallel), OpenAI API (`gpt-4o-mini`, `text-embedding-3-small`)
- **Vector DB**: FAISS (`faiss-cpu`, `langchain-community`)
- **Data Source**: AI Hub 공공 의료 QA 데이터 (오프라인 적재)
- **Frontend**: Gradio
- **Test**: pytest

## 📁 프로젝트 아키텍처
```text
healthcare_chatbot/
├── app.py                      # 실행 진입점
├── .env.example                # 환경변수 템플릿
├── requirements.txt
│
├── config/
│   └── settings.py             # 전역 설정(모델/임계값/AI Hub 경로·필드매핑)
│
├── data/                       # 데이터 접근 계층
│   ├── faq_repository.py       # 공개 API: 소스 선택 + 폴백 + 캐싱
│   ├── schema.py               # FAQItem 스키마 + 정규화/검증
│   ├── sample_faqs.py          # 내장 데모(폴백) 데이터
│   └── loaders/
│       ├── base.py             # FAQLoader 인터페이스(ABC)
│       ├── aihub_loader.py     # AI Hub JSON 로더(스키마 유연 파싱)
│       └── sample_loader.py    # 폴백 로더
│
├── core/                       # AI 코어
│   ├── retriever.py            # FAISS + 데이터 변경 감지 재빌드 + search_with_score
│   ├── prompts.py              # 프롬프트(RAG/의도분류/재작성)
│   └── llm_builder.py          # LCEL + RunnableParallel 체인 조립
│
├── service/
│   └── chat_service.py         # 검증→의도분류→재작성→검색→생성 오케스트레이션
│
├── ui/
│   └── gradio_app.py           # Gradio 화면
│
├── scripts/
│   ├── download_aihub.sh       # aihubshell 다운로드 래퍼
│   └── build_index.py          # FAISS 인덱스 오프라인 사전 빌드
│
├── tests/                      # pytest (네트워크/비용 0)
│   ├── sample_aihub/           # 모의 AI Hub JSON
│   ├── test_aihub_loader.py    # 로더 파싱/스킵/디덥
│   ├── test_validation.py      # 입력 가드레일
│   ├── test_retriever.py       # 인덱스 빌드/재로드/재빌드/거리
│   └── test_service.py         # 전체 흐름(스텁 LLM)
│
└── faq_faiss_index/            # (자동 생성) FAISS 인덱스 + 데이터 지문
```

## 📦 AI Hub 데이터 취득 방법 (중요)
AI Hub 데이터는 **실시간 조회 API가 아니라** 다음 오프라인 절차로 취득합니다.
1. [aihub.or.kr](https://aihub.or.kr) 로그인 → 사용할 의료 QA 데이터셋 소개 페이지에서
   **[다운로드] 승인** (보건의료 데이터는 안심존 신청이 추가로 필요할 수 있음).
2. AI Hub **API Key** 발급.
3. 데이터 다운로드(분할압축 zip → 병합/해제):
   ```bash
   export AIHUB_API_KEY='발급받은-키'
   export AIHUB_DATASET_KEY='데이터셋 dataSetSn'
   bash scripts/download_aihub.sh
   ```
   → 압축 해제된 JSON이 `./data/raw/aihub/` 아래에 준비됩니다.
4. (선택) 인덱스 사전 빌드: `python scripts/build_index.py`

> AI Hub JSON 스키마는 데이터셋/버전마다 다릅니다. 본인 데이터셋의 키 이름이 다르면
> `config/settings.py`의 `AIHUB_FIELD_MAP`(question_keys/answer_keys/category_keys 등)만
> 수정하면 됩니다. 로더 코드는 건드릴 필요가 없습니다.

## 🚀 설치 및 실행
```bash
# 1) 가상환경
python3 -m venv .venv && source .venv/bin/activate

# 2) 패키지 설치
pip install -r requirements.txt

# 3) 환경변수
cp .env.example .env   # OPENAI_API_KEY 등 입력

# 4) 실행 (AI Hub 데이터가 없으면 내장 샘플로 동작)
python app.py
```

## ✅ 테스트
```bash
pytest -q
```
OpenAI 키나 네트워크 없이 동작하도록, 임베딩/LLM은 결정적 더미·스텁으로 대체했습니다.
자세한 테스트 설계는 `tests/`를 참고하세요.
