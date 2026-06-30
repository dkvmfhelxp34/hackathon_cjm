#!/usr/bin/env bash
# agent1 PDF 파서 원클릭 실행 (재현용)
# - python3.10+ 인터프리터 자동 탐지 → opendataloader-pdf 보장 → 파싱
# - 옵션: --with-agent2 면 파싱 결과를 agent2(하이브리드 추출)까지 연결
#
# 사용:
#   ./run.sh <input.pdf>                 # 파싱만 → agent1_output.json
#   ./run.sh <input.pdf> --with-agent2   # agent1 → agent2(hybrid) 전체 파이프라인
set -euo pipefail
cd "$(dirname "$0")"

PDF="${1:-}"
WITH_AGENT2="${2:-}"

# 1) python3.10+ 자동 탐지
PY=""
for cand in python3.13 python3.12 python3.11 python3.10 /opt/anaconda3/bin/python3.11 python3; do
  if command -v "$cand" >/dev/null 2>&1; then
    ver="$("$cand" -c 'import sys;print("%d%d"%sys.version_info[:2])' 2>/dev/null || echo 0)"
    if [ "$ver" -ge 310 ] 2>/dev/null; then PY="$cand"; break; fi
  fi
done
if [ -z "$PY" ]; then
  echo "[오류] Python 3.10+ 인터프리터를 못 찾았습니다. (opendataloader-pdf 요구)" >&2
  echo "      예) brew install python@3.12  후 다시 실행" >&2
  exit 1
fi
echo "[env] Python: $($PY --version 2>&1) ($PY)"

# 2) Java 확인(opendataloader 엔진)
if ! java -version >/dev/null 2>&1; then
  echo "[경고] Java(11+)가 안 보입니다. opendataloader-pdf 실행에 필요합니다 (brew install openjdk)." >&2
fi

# 3) 의존성 보장
if ! "$PY" -c "import opendataloader_pdf" >/dev/null 2>&1; then
  echo "[setup] opendataloader-pdf 설치 중..."
  "$PY" -m pip install -q -U -r requirements.txt
fi

# 4) 파싱
"$PY" agent1_parse.py ${PDF:+"$PDF"}

# 5) 옵션: agent2 연결 (agent2는 stdlib만 쓰므로 시스템 python3로 충분)
if [ "$WITH_AGENT2" = "--with-agent2" ]; then
  echo ""
  echo "=== agent2(hybrid) 연결 실행 ==="
  AGENT1_OUTPUT="$(pwd)/agent1_output.json" AGENT2_BACKEND=hybrid python3 ../agent2/agent2_extract.py
fi
