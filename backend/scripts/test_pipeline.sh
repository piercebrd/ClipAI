#!/usr/bin/env bash
# ClipAI — test end-to-end pipeline
# Usage: ./scripts/test_pipeline.sh [youtube_url]

set -euo pipefail

URL="${1:-https://www.youtube.com/watch?v=dQw4w9WgXcQ}"
PORT=8765
BASE="http://localhost:$PORT"
SERVER_PID=""

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}✔ $1${NC}"; }
fail() { echo -e "${RED}✘ $1${NC}"; exit 1; }
info() { echo -e "${YELLOW}→ $1${NC}"; }

cleanup() {
  if [ -n "$SERVER_PID" ]; then
    kill "$SERVER_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

# ── 1. Start server ──────────────────────────────────────────────
info "Starting FastAPI server on port $PORT..."
source "$(dirname "$0")/../venv/bin/activate"
cd "$(dirname "$0")/.."
uvicorn app.main:app --port $PORT --log-level error &
SERVER_PID=$!
sleep 3

# ── 2. Health check ──────────────────────────────────────────────
info "Checking /health..."
HEALTH=$(curl -sf "$BASE/health" || echo '{}')
STATUS=$(echo "$HEALTH" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status',''))")
FFMPEG=$(echo "$HEALTH" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('ffmpeg',''))")

[ "$STATUS" = "ok" ] && pass "/health → ok" || fail "/health returned: $HEALTH"
[ "$FFMPEG" = "True" ] && pass "FFmpeg disponible" || echo -e "${YELLOW}⚠ FFmpeg non trouvé${NC}"

# ── 3. Submit analyze ────────────────────────────────────────────
info "Submitting URL: $URL"
RESPONSE=$(curl -sf -X POST "$BASE/analyze" \
  -H "Content-Type: application/json" \
  -d "{\"url\": \"$URL\"}")
JOB_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['job_id'])")
[ -n "$JOB_ID" ] && pass "Job créé: $JOB_ID" || fail "Pas de job_id dans la réponse"

# ── 4. Poll status ───────────────────────────────────────────────
info "Polling /status/$JOB_ID..."
MAX_WAIT=300  # 5 minutes max
ELAPSED=0
PREV_STEP=""

while [ $ELAPSED -lt $MAX_WAIT ]; do
  JOB=$(curl -sf "$BASE/status/$JOB_ID")
  STEP=$(echo "$JOB" | python3 -c "import sys,json; print(json.load(sys.stdin)['step'])")
  MSG=$(echo "$JOB" | python3 -c "import sys,json; print(json.load(sys.stdin)['message'])")
  PROGRESS=$(echo "$JOB" | python3 -c "import sys,json; print(json.load(sys.stdin)['progress'])")

  if [ "$STEP" != "$PREV_STEP" ]; then
    echo -e "  [${PROGRESS}%] ${STEP}: ${MSG}"
    PREV_STEP="$STEP"
  fi

  if [ "$STEP" = "error" ]; then
    fail "Pipeline en erreur: $MSG"
  fi

  # Check for a terminal success step
  if [[ "$STEP" == "transcribed" || "$STEP" == "analyzed" || "$STEP" == "done" ]]; then
    break
  fi

  sleep 5
  ELAPSED=$((ELAPSED + 5))
done

# ── 5. Validate result ───────────────────────────────────────────
STEP=$(echo "$JOB" | python3 -c "import sys,json; print(json.load(sys.stdin)['step'])")

if [ "$STEP" = "transcribed" ]; then
  WORD_COUNT=$(echo "$JOB" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('words', [])))")
  LANG=$(echo "$JOB" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('language', '?'))")
  pass "Transcription complète: $WORD_COUNT mots, langue=$LANG"
elif [ "$STEP" = "analyzed" ] || [ "$STEP" = "done" ]; then
  pass "Pipeline complet: $STEP"
else
  fail "Timeout — dernière étape: $STEP ($MSG)"
fi

echo ""
echo -e "${GREEN}══ Tous les tests passés ══${NC}"
