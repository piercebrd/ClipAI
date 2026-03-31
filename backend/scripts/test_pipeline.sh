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
elif [ "$STEP" = "analyzed" ]; then
  WORD_COUNT=$(echo "$JOB" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('words', [])))")
  LANG=$(echo "$JOB" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('language', '?'))")
  CLIP_COUNT=$(echo "$JOB" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('clips', [])))")
  TOP_SCORE=$(echo "$JOB" | python3 -c "import sys,json; d=json.load(sys.stdin); clips=d.get('clips',[]); print(clips[0]['score'] if clips else 0)")
  pass "Transcription: $WORD_COUNT mots ($LANG)"
  pass "Claude: $CLIP_COUNT clips détectés (meilleur score: $TOP_SCORE)"
  echo "$JOB" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for c in d.get('clips', [])[:3]:
    print(f\"  [{c['score']}] {c['title']} ({c['start']}s→{c['end']}s) [{c['type']}]\")
"

  # ── 6. Test render (premier clip seulement) ──────────────────
  info "Test rendu FFmpeg (clip 1)..."
  FIRST_CLIP=$(echo "$JOB" | python3 -c "
import sys, json
d = json.load(sys.stdin)
c = d['clips'][0]
print(c['id'], c['start'], c['end'])
")
  CLIP_ID=$(echo "$FIRST_CLIP" | awk '{print $1}')
  CLIP_START=$(echo "$FIRST_CLIP" | awk '{print $2}')
  CLIP_END=$(echo "$FIRST_CLIP" | awk '{print $3}')

  RENDER_RESP=$(curl -sf -X POST "$BASE/render" \
    -H "Content-Type: application/json" \
    -d "{\"job_id\": \"$JOB_ID\", \"clips\": [{\"id\": \"$CLIP_ID\", \"start\": $CLIP_START, \"end\": $CLIP_END}]}")
  RENDER_ID=$(echo "$RENDER_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['render_id'])")
  [ -n "$RENDER_ID" ] && pass "Render lancé: $RENDER_ID" || fail "Pas de render_id"

  # Poll render status
  R_ELAPSED=0
  while [ $R_ELAPSED -lt 120 ]; do
    RJOB=$(curl -sf "$BASE/render/status/$RENDER_ID")
    RSTEP=$(echo "$RJOB" | python3 -c "import sys,json; print(json.load(sys.stdin)['step'])")
    RMSG=$(echo "$RJOB" | python3 -c "import sys,json; print(json.load(sys.stdin)['message'])")
    [ "$RSTEP" = "done" ] && break
    echo "  [render] $RMSG"
    sleep 3
    R_ELAPSED=$((R_ELAPSED + 3))
  done

  RFILES=$(echo "$RJOB" | python3 -c "import sys,json; print(json.load(sys.stdin).get('files','[]'))")
  if [ "$RSTEP" = "done" ]; then
    pass "FFmpeg rendu OK — fichiers: $RFILES"
  else
    fail "Render timeout ou erreur: $RMSG"
  fi

elif [ "$STEP" = "done" ]; then
  pass "Pipeline complet"
else
  fail "Timeout — dernière étape: $STEP ($MSG)"
fi

echo ""
echo -e "${GREEN}══ Tous les tests passés ══${NC}"
