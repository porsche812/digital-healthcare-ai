#!/usr/bin/env bash
# =============================================================================
# AI Hub 헬스케어 QA 데이터 다운로드 헬퍼 (aihubshell 래퍼)
# =============================================================================
# 전제 조건:
#   1) aihub.or.kr 회원가입 및 로그인
#   2) 사용할 데이터셋 소개 페이지에서 [다운로드] 버튼을 눌러 "이용 승인" 완료
#      (보건의료 데이터는 안심존 신청이 추가로 필요할 수 있음)
#   3) AI Hub API Key 발급
#   4) .env 에 AIHUB_API_KEY, (settings 의) AIHUB_DATASET_KEY 설정
#
# 데이터는 실시간 조회 API 가 아니라 분할압축(zip) 파일로 내려받아 병합/해제합니다.
# 받은 JSON 들을 settings.AIHUB_DATA_DIR (기본 ./data/raw/aihub) 로 옮기면 됩니다.
# =============================================================================
set -euo pipefail

DATASET_KEY="${AIHUB_DATASET_KEY:-}"
API_KEY="${AIHUB_API_KEY:-}"
DEST="${AIHUB_DATA_DIR:-./data/raw/aihub}"

if [[ -z "$DATASET_KEY" || -z "$API_KEY" ]]; then
  echo "AIHUB_DATASET_KEY 와 AIHUB_API_KEY 환경변수를 먼저 설정하세요." >&2
  echo "  export AIHUB_DATASET_KEY=<데이터셋 dataSetSn>" >&2
  echo "  export AIHUB_API_KEY='<발급받은 API Key>'" >&2
  exit 1
fi

# 1) aihubshell 설치(최초 1회)
if ! command -v aihubshell >/dev/null 2>&1; then
  echo "[1/3] aihubshell 설치"
  curl -sL -o aihubshell https://api.aihub.or.kr/api/aihubshell.do
  chmod +x aihubshell
  sudo mv aihubshell /usr/local/bin/ 2>/dev/null || export PATH="$PWD:$PATH"
fi

# 2) 다운로드 (분할압축 .zip.part* 형태로 받아짐)
echo "[2/3] 데이터셋(${DATASET_KEY}) 다운로드"
mkdir -p "$DEST"
( cd "$DEST" && aihubshell -mode d -datasetkey "$DATASET_KEY" -aihubapikey "$API_KEY" )

# 3) 분할압축 병합 + 해제
echo "[3/3] 분할압축 병합 및 해제"
( cd "$DEST"
  # 분할 파일 병합
  find . -name "*.zip.part*" | sed 's/\.part[0-9]*$//' | sort -u | while read -r z; do
    find . -name "$(basename "$z").part*" -print0 | sort -zt'.' -k2V | xargs -0 cat > "$z"
  done
  # zip 해제(한글 깨짐 방지를 위해 unzip -O 또는 7z 권장)
  for f in $(find . -name "*.zip"); do unzip -o -O cp949 "$f" -d "${f%.zip}" || unzip -o "$f" -d "${f%.zip}"; done
)

echo "✅ 완료. JSON 라벨링데이터가 '${DEST}' 하위에 준비되었습니다."
echo "   이후 'python scripts/build_index.py' 로 FAISS 인덱스를 미리 빌드할 수 있습니다."
