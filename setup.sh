#!/usr/bin/env bash
# setup.sh — first-time local development setup for ProposalPilot AI
# Run from the proposal-pilot/ directory: bash setup.sh

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

ok()   { echo -e "${GREEN}[ok]${NC} $*"; }
warn() { echo -e "${YELLOW}[warn]${NC} $*"; }
err()  { echo -e "${RED}[error]${NC} $*"; exit 1; }
step() { echo -e "\n${GREEN}==> $*${NC}"; }

# ---- Check working directory ----
[[ -f "backend/main.py" ]] || err "Run this script from the proposal-pilot/ directory."

# ---- .env setup ----
step ".env"
if [[ ! -f .env ]]; then
    cp .env.example .env
    ok "Created .env from .env.example"
else
    ok ".env already exists"
fi

# Generate JWT_SECRET if still default
if grep -q "JWT_SECRET=change-me" .env; then
    SECRET=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
    # Works on both Linux (sed -i) and macOS (sed -i '')
    sed -i.bak "s/JWT_SECRET=change-me-before-deploy/JWT_SECRET=${SECRET}/" .env && rm -f .env.bak
    ok "Generated JWT_SECRET"
fi

# Warn if ANTHROPIC_API_KEY is empty and using anthropic provider
if grep -q "LLM_PROVIDER=anthropic" .env && grep -qE "ANTHROPIC_API_KEY=$" .env; then
    warn "ANTHROPIC_API_KEY is empty. Edit .env before generating drafts."
fi

# ---- Python virtual environment ----
step "Python environment"
if [[ ! -d backend/.venv ]]; then
    python3 -m venv backend/.venv
    ok "Created backend/.venv"
else
    ok "backend/.venv already exists"
fi

source backend/.venv/bin/activate
pip install -q --upgrade pip
pip install -q -r backend/requirements.txt
ok "Python dependencies installed"

# ---- Database ----
step "Database"
python3 -c "from backend.database import init_db; init_db()"
ok "Database initialized"

# ---- Seed capabilities (only if empty) ----
step "Capabilities"
CAP_COUNT=$(python3 -c "from backend.db.crud import get_all_capabilities; print(len(get_all_capabilities()))")
if [[ "$CAP_COUNT" == "0" ]]; then
    python3 -m backend.capabilities.seed_capabilities
    ok "Capabilities seeded"
else
    ok "Skipped seed: ${CAP_COUNT} capabilities already exist"
fi

# ---- Node / frontend deps ----
step "Frontend dependencies"
if ! command -v node &>/dev/null; then
    warn "Node.js not found. Install Node 20+ or use fnm:"
    warn "  curl -fsSL https://fnm.vercel.app/install | bash && fnm install 20"
else
    NODE_VER=$(node --version)
    ok "Node ${NODE_VER} found"
    (cd frontend && npm install --silent)
    ok "Frontend dependencies installed"
fi

# ---- Done ----
echo ""
echo "============================================"
echo " Setup complete. Start the app:"
echo "============================================"
echo ""
echo " Terminal 1 (backend):"
echo "   source backend/.venv/bin/activate"
echo "   uvicorn backend.main:app --reload"
echo ""
echo " Terminal 2 (frontend):"
echo "   cd frontend && npm run dev"
echo ""
echo " Then open http://localhost:5173/login"
echo " and register your account."
echo ""
echo " For Docker deployment, see BETA_SETUP.md"
echo "============================================"
