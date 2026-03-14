# 디지털 헬스케어 AI 챗봇

기존 병원/헬스케어 FAQ 데이터를 바탕으로, 예외 처리와 검색(RAG) 파이프라인이 탑재된 도메인 특화 AI 챗봇입니다.

## 주요 기능
- **RAG 기반 검색**: 사용자의 질문과 FAQ 데이터 간의 키워드 및 의미 기반 매칭 알고리즘
- **안전한 가드레일**: 의료 도메인의 특성을 반영하여 FAQ에 없는 내용은 "고객센터 문의"로 안전하게 예외 처리 (환각 현상 방지)
- **Gradio 웹 UI**: 사용자 친화적인 웹 기반 채팅 인터페이스 제공

## 기술 스택
- Python 3.11+
- Gradio
- LangChain & OpenAI API

## 로컬 실행 방법 (Mac 환경 기준)

### 1. 가상환경 세팅 및 패키지 설치
터미널을 열고 아래 명령어를 순서대로 실행합니다.

```bash
# 가상환경 생성 및 활성화
python3 -m venv .venv
source .venv/bin/activate

# 필수 패키지 설치
pip install -r requirements.txt