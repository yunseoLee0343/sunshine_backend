#!/usr/bin/env bash
# Quality Gate — TICKET-014G
#
# Runs: Ruff lint → Ruff format check → Pytest + coverage
# Exits non-zero on any failure so CI can gate merges.
#
# Usage:
#   bash scripts/check_gate.sh            # full suite
#   SKIP_TESTS=1 bash scripts/check_gate.sh  # lint + format only

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}[PASS]${NC} $*"; }
fail() { echo -e "${RED}[FAIL]${NC} $*"; exit 1; }
step() { echo -e "\n${YELLOW}──── $* ────${NC}"; }

# ── 1. Ruff lint ─────────────────────────────────────────────────────────────
step "Ruff lint"
python -m ruff check app/ tests/ && pass "Ruff lint" || fail "Ruff lint: violations found"

# ── 2. Ruff format ───────────────────────────────────────────────────────────
step "Ruff format"
python -m ruff format app/ tests/ --check && pass "Ruff format" || fail "Ruff format: files would be reformatted — run: python -m ruff format app/ tests/"

# ── 3. Pytest + coverage gate ────────────────────────────────────────────────
if [[ "${SKIP_TESTS:-0}" == "1" ]]; then
    echo "SKIP_TESTS=1 — skipping test suite"
else
    step "Pytest + coverage (≥80%)"
    python -m pytest \
        --ignore=tests/e2e \
        -q \
        --tb=short \
        --cov \
        --cov-report=term-missing \
        --cov-fail-under=80 \
        && pass "Tests + coverage ≥ 80%" \
        || fail "Tests or coverage gate failed"
fi

echo -e "\n${GREEN}All quality gates passed.${NC}"
