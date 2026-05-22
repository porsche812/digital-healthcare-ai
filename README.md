# 🏥 디지털 헬스케어 AI 챗봇 (Digital Healthcare RAG Chatbot)

AI Hub 공공 의료 QA 데이터를 적재하여, FAISS 벡터 기반 의미 검색과 예외 처리(가드레일)
파이프라인을 갖춘 도메인 특화 멀티턴 AI 챗봇입니다. 데이터 적재 → 인덱싱 → 검색 → 생성의
각 단계가 계층으로 분리되어 있어 데이터 소스 교체와 RAG 고도화가 쉽습니다.

## ✨ 주요 기능
- **AI Hub 공공 의료 데이터 적재(실데이터 전용)**: 하드코딩 데이터를 제거하고, AI Hub에서
  내려받은 의료 QA JSON을 정규화·중복제거하여 적재하는 **로더 계층**으로 대체. 데이터가
  없으면 폴백 없이 명확한 에러로 중단합니다.
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
- **Vector DB**: FAISS (`faiss-cpu` 직접 사용 — community 래퍼 미사용)
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
사용 데이터셋: **초거대 AI 헬스케어 질의응답 데이터 (dataSetSn=71762)**.
AI Hub 데이터는 **실시간 조회 API가 아니라** 다음 오프라인 절차로 취득합니다.
1. [aihub.or.kr](https://aihub.or.kr) 로그인 → 데이터셋 소개 페이지에서 **[다운로드] 승인**.
2. AI Hub **API Key** 발급.
3. 데이터 다운로드(분할압축 zip → 병합/해제):
   ```bash
   export AIHUB_API_KEY='발급받은-키'
   export AIHUB_DATASET_KEY='71762'
   bash scripts/download_aihub.sh
   ```
   또는 `aihubshell`로 직접 받은 뒤, `TL.zip`/`VL.zip`(라벨링데이터)을 압축 해제하면
   `2.답변/{질병분류}/{질병명}/{질문유형}/HC-A-*.json` 구조로 풀립니다.

### 이 데이터셋의 구조와 적재 방식
질문(`1.질문`)과 답변(`2.답변`)이 별도 폴더로 분리되어 있고 둘을 잇는 공통 ID가 없습니다.
답변 파일 한 건이 질병·질문유형·진료과·상세답변을 모두 담고 있어, **답변 파일(HC-A-*.json)만
적재**해도 RAG 검색에 충분합니다. 전용 로더(`data/loaders/aihub_answer_loader.py`)가:
- `answer.intro + body + conclusion` → 답변 본문으로 병합
- `disease_name.kor + intention` → 검색용 의사(擬似) 질문
- `department[0]` → 진료과(카테고리)

### ⚠️ 비용 통제 (필수)
답변 파일이 **약 221만 개**라 전부 임베딩하면 비용·시간이 큽니다. 그래서 **진료과별/전체
상한으로 샘플링**합니다(전체에서 고르게 stride 추출). `.env`에서 조정:
```
AIHUB_PER_CATEGORY_LIMIT=150   # 진료과별 최대 (0=무제한)
AIHUB_TOTAL_LIMIT=3000         # 전체 최대 (0=무제한)
```
기본값(진료과당 150, 전체 3000)이면 임베딩 비용은 대략 1달러 안쪽입니다.

> **데이터를 복사하지 마세요.** 받은 폴더를 그대로 두고 `.env`의 `AIHUB_DATA_DIR`이
> 그 폴더(또는 상위)를 가리키게만 하면 됩니다. 로더가 하위에서 `HC-A-*.json`을 찾습니다.

## 🚀 설치 및 실행
```bash
# 1) 가상환경
python3 -m venv .venv && source .venv/bin/activate

# 2) 패키지 설치
pip install -r requirements.txt

# 3) 환경변수
cp .env.example .env   # OPENAI_API_KEY 등 입력

# 4) 실행 (AI Hub 데이터 경로가 .env 에 올바로 설정되어 있어야 함)
python scripts/build_index.py   # FAISS 인덱스 사전 빌드(권장)
python app.py
```

## ✅ 테스트
```bash
pytest -q
```
테스트는 OpenAI 키나 네트워크 없이 동작하도록, 임베딩/LLM은 결정적 더미·스텁으로 대체했습니다.
자세한 테스트 설계는 `tests/`를 참고하세요.

## 🧭 설계 결정 (Design Decisions)
모델·라이브러리 선택보다, "왜 이렇게 했는지"의 의사결정을 기록합니다.

### 1. AI Hub 데이터를 "실시간 호출"이 아니라 "로더 계층"으로 적재한 이유
AI Hub 데이터는 REST 쿼리로 실시간 조회되는 형태가 아니라, 로그인 → 데이터셋 이용 승인
→ `aihubshell` 로 분할압축(zip) 다운로드 → 병합·해제의 오프라인 절차로 취득됩니다.
따라서 "런타임에 외부 API를 호출"하는 설계는 불가능하며, 내려받아 압축 해제한 JSON을
읽어 표준 스키마(`FAQItem`)로 정규화하는 **데이터 로더 계층**으로 분리했습니다. 데이터
출처가 바뀌어도 상위 계층(검색·서비스)은 영향을 받지 않습니다.

### 2. 질문/답변이 분리된 데이터에서 "답변 파일만" 적재한 이유
사용한 데이터셋(초거대 AI 헬스케어 질의응답, dataSetSn=71762)은 질문(`1.질문`)과
답변(`2.답변`)이 별도 폴더로 분리되어 있고 둘을 잇는 공통 ID가 없습니다. 그러나 답변
파일 한 건이 질병명·질문유형(intention)·진료과(department)·상세 답변(intro/body/conclusion)을
모두 포함하므로, "질문 임베딩 → 가장 가까운 답변 검색" 방식의 RAG에는 **답변 파일만으로
충분**하다고 판단해 답변 중심으로 적재했습니다.

### 3. 약 221만 건 중 일부만 샘플링한 이유 (비용·품질 트레이드오프)
답변 파일은 약 2,212,306건입니다. 전부 임베딩하면 비용·시간·인덱스 용량이 과대해지므로,
검색 품질을 유지하는 선에서 샘플링했습니다. 무작위가 아니라 (1) 전체 목록에서 일정 간격으로
뽑는 **stride 샘플링**으로 데이터 전반을 고르게 커버하고, (2) **질병별 상한**으로 특정
질병이 인덱스를 독식하지 않도록 다양성을 확보했습니다.

### 4. 도메인을 "내과"로 좁힌 이유
초기에는 56개 진료과를 얕게 샘플링했더니, 흔한 질병(예: 위염)이 샘플에서 누락되어 검색이
엉뚱한 문서를 반환하는 커버리지 공백이 발생했습니다. 표본 분석 결과 **내과 계열이 전체의
약 37%로 압도적**이었고, 일반 사용자의 건강 상담 수요(소화기·내분비·순환기 등)와도
부합하여, 도메인을 내과로 집중했습니다. 범위를 못 정한 것이 아니라, 한 진료과의 질병
커버리지를 깊게 확보해 "물어보면 대체로 답하는" 밀도를 얻기 위한 **전략적 축소**입니다.

### 5. 검색 임계값을 데이터 분포 측정으로 결정 (감이 아니라 측정)
OOD(도메인 밖) 질문을 거부하는 L2 거리 임계값을, 임의값(초기 1.5) 대신 실제 거리 분포를
측정해 정했습니다. 정답 매칭(예: "대사 증후군 검진")은 거리 약 0.6, 오답 매칭(위염→관절염)은
약 0.9로 관측되어, 둘을 가르는 **0.8**로 설정했습니다. 임계값은 `.env`로 조정 가능합니다.

### 6. 데이터 변경 시 인덱스 자동 재빌드 (지문 기반 캐시 무효화)
FAISS 인덱스를 디스크에 캐시하되, 데이터의 내용 지문(SHA-256)을 함께 저장합니다. 적재
데이터가 바뀌면 지문 불일치를 감지해 옛 인덱스를 그대로 쓰지 않고 **자동 재빌드**합니다.
(원본 코드의 "데이터가 바뀌어도 옛 인덱스를 로드"하던 버그를 수정.)

### 7. langchain-community 의존성 제거 (버전 충돌 해결)
원본은 `langchain_community.vectorstores.FAISS`를 사용했으나, 이 래퍼는 구버전
langchain-core(<1.0)를 요구해 현재 환경의 core 1.x와 충돌합니다. 그래서 community를
거치지 않고 **faiss 를 직접 사용**(IndexFlatL2 + 자체 docstore)하도록 재작성해 의존성
충돌을 근본적으로 제거했습니다.

### 8. 멀티턴·파이프라인·가드레일
- **질문 재작성(Query Rewriting)**: 직전 대화 문맥으로 짧은 꼬리 질문을 검색용 완전
  문장으로 보강(검색은 재작성 질문, 답변 생성은 원본 질문 사용).
- **LCEL + RunnableParallel**: 답변 생성과 출처(메타데이터) 표기를 병렬 실행 후 병합.
- **가드레일**: 입력 검증(공백/길이/숫자) + 의도 분류(인사·불만·잡담 분기) + 거리 임계값 OOD 차단.

### 9. 테스트 전략 (OpenAI 키·비용·네트워크 0)
임베딩은 결정적 더미, LLM 체인은 스텁으로 주입(의존성 주입 설계) 하여, API 비용·키 없이
파이프라인 로직(로더 파싱/필터/샘플링, 인덱스 빌드·재빌드, 검색 임계값, 의도 라우팅,
출처 표기)을 검증합니다. OpenAI 자체 성능(임베딩 품질·답변 자연스러움)은 단위 테스트
대상이 아니라 실행 시 수동 확인 영역으로 분리했습니다.
