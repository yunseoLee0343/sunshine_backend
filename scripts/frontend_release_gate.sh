#!/usr/bin/env bash
# Frontend MVP Release Gate — TICKET-042
#
# Runs: TypeScript check → ESLint → Vite build → API smoke test
# Generates: docs/frontend_release_report.md (filled from template)
# Exits non-zero on any automated gate failure.
#
# Usage:
#   bash scripts/frontend_release_gate.sh
#   SKIP_SMOKE=1 bash scripts/frontend_release_gate.sh   # skip live API checks

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FRONTEND="$ROOT/frontend"
DOCS="$ROOT/docs"
REPORT="$DOCS/frontend_release_report.md"
TEMPLATE="$DOCS/frontend_release_report_template.md"
TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S')"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

pass()  { echo -e "${GREEN}[PASS]${NC} $*"; }
fail()  { echo -e "${RED}[FAIL]${NC} $*"; GATE_FAILED=1; }
step()  { echo -e "\n${YELLOW}──── $* ────${NC}"; }
info()  { echo -e "${CYAN}[INFO]${NC} $*"; }

GATE_FAILED=0

cd "$FRONTEND"

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════╗"
echo "║   Sunshine Frontend — MVP Release Gate       ║"
echo "║   TICKET-042                                 ║"
echo "╚══════════════════════════════════════════════╝"
echo -e "${NC}"
info "Timestamp : $TIMESTAMP"
info "Frontend  : $FRONTEND"

# ── 1. TypeScript ─────────────────────────────────────────────────────────────
step "TypeScript type check (tsc --noEmit)"
if npx tsc --noEmit 2>&1; then
  pass "TypeScript: no type errors"
  TS_RESULT="PASS"
else
  fail "TypeScript: type errors found"
  TS_RESULT="FAIL"
fi

# ── 2. ESLint ─────────────────────────────────────────────────────────────────
step "ESLint"
if npm run lint 2>&1; then
  pass "ESLint: 0 errors"
  LINT_RESULT="PASS"
else
  fail "ESLint: violations found"
  LINT_RESULT="FAIL"
fi

# ── 3. Production build ───────────────────────────────────────────────────────
step "Vite production build"
if npm run build 2>&1; then
  BUNDLE_SIZE="$(du -sh dist/assets/*.js 2>/dev/null | awk '{print $1}' | head -1)"
  pass "Build succeeded (JS bundle: ${BUNDLE_SIZE:-unknown})"
  BUILD_RESULT="PASS"
else
  fail "Build failed"
  BUILD_RESULT="FAIL"
fi

# ── 4. API smoke test (optional — requires backend running on :8000) ──────────
step "API smoke test (backend health + core endpoints)"
SMOKE_RESULT="SKIP"

if [[ "${SKIP_SMOKE:-0}" == "1" ]]; then
  info "SKIP_SMOKE=1 — skipping live API checks"
  SMOKE_RESULT="SKIP"
elif command -v curl &>/dev/null; then
  BACKEND="${BACKEND_URL:-http://localhost:8000}"
  SMOKE_ERRORS=0

  info "Backend target: $BACKEND"

  # 4a. Liveness probe
  if curl -sf "$BACKEND/healthz" -o /dev/null 2>&1; then
    pass "GET /healthz → 200"
  else
    fail "GET /healthz failed — is the backend running?"
    SMOKE_ERRORS=$((SMOKE_ERRORS + 1))
  fi

  # 4b. Readiness probe
  if curl -sf "$BACKEND/readyz" -o /dev/null 2>&1; then
    pass "GET /readyz → 200"
  else
    fail "GET /readyz failed — database may be down"
    SMOKE_ERRORS=$((SMOKE_ERRORS + 1))
  fi

  # 4c. Home endpoint (requires X-User-Id header)
  DEMO_USER="7923c9bd-80d8-d2d1-1937-b9e0e7e28887"
  if curl -sf "$BACKEND/home" \
       -H "X-User-Id: $DEMO_USER" \
       -o /dev/null 2>&1; then
    pass "GET /home → 200"
  else
    fail "GET /home failed"
    SMOKE_ERRORS=$((SMOKE_ERRORS + 1))
  fi

  if [[ $SMOKE_ERRORS -eq 0 ]]; then
    SMOKE_RESULT="PASS"
    pass "All API smoke checks passed"
  else
    SMOKE_RESULT="FAIL ($SMOKE_ERRORS errors)"
    GATE_FAILED=1
  fi
else
  info "curl not found — skipping smoke test"
  SMOKE_RESULT="SKIP (curl unavailable)"
fi

# ── 5. Generate release report ────────────────────────────────────────────────
step "Generating release report"

if [[ -f "$TEMPLATE" ]]; then
  OVERALL="PASS"
  [[ $GATE_FAILED -ne 0 ]] && OVERALL="FAIL"

  sed \
    -e "s/{{TIMESTAMP}}/$TIMESTAMP/g" \
    -e "s/{{TS_RESULT}}/$TS_RESULT/g" \
    -e "s/{{LINT_RESULT}}/$LINT_RESULT/g" \
    -e "s/{{BUILD_RESULT}}/$BUILD_RESULT/g" \
    -e "s/{{SMOKE_RESULT}}/$SMOKE_RESULT/g" \
    -e "s/{{OVERALL}}/$OVERALL/g" \
    "$TEMPLATE" > "$REPORT"

  pass "Release report written to: $REPORT"
else
  info "Template not found at $TEMPLATE — skipping report generation"
fi

# ── Final verdict ─────────────────────────────────────────────────────────────
echo ""
if [[ $GATE_FAILED -eq 0 ]]; then
  echo -e "${GREEN}══════════════════════════════════════${NC}"
  echo -e "${GREEN}  All automated gates passed.         ${NC}"
  echo -e "${GREEN}  Proceed to manual smoke checklist.  ${NC}"
  echo -e "${GREEN}══════════════════════════════════════${NC}"
  exit 0
else
  echo -e "${RED}══════════════════════════════════════${NC}"
  echo -e "${RED}  One or more gates FAILED.           ${NC}"
  echo -e "${RED}  Fix errors before releasing.        ${NC}"
  echo -e "${RED}══════════════════════════════════════${NC}"
  exit 1
fi
