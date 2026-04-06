#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# Faculty Information Retrieval System — One-Time Setup
# Run this once from the project root: ./setup.sh
# ─────────────────────────────────────────────────────────────────────────────

set -e

CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║     Faculty Information Retrieval System — Setup         ║"
echo "║     Hybrid BM25 + Semantic Search · 100% Free            ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "${YELLOW}Checking prerequisites...${NC}"
if ! command -v python3 &>/dev/null; then echo -e "${RED}Python3 not found${NC}"; exit 1; fi
if ! command -v node &>/dev/null; then echo -e "${RED}Node.js not found${NC}"; exit 1; fi
echo -e "  ${GREEN}✓ Python $(python3 --version) / Node $(node --version)${NC}"

echo -e "\n${YELLOW}[1/5] Creating Python virtual environment...${NC}"
python3 -m venv venv
source venv/bin/activate
echo -e "  ${GREEN}✓ venv created${NC}"

echo -e "\n${YELLOW}[2/5] Installing Python dependencies...${NC}"
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo -e "  ${GREEN}✓ Python packages installed${NC}"

echo -e "\n${YELLOW}[3/5] Downloading spaCy model...${NC}"
python3 -m spacy download en_core_web_sm -q 2>/dev/null || echo -e "  ${YELLOW}⚠ spaCy model skipped (non-critical)${NC}"
echo -e "  ${GREEN}✓ Done${NC}"

echo -e "\n${YELLOW}[4/5] Creating data directories...${NC}"
mkdir -p data/cache data/embeddings
echo -e "  ${GREEN}✓ data/ directories created${NC}"

echo -e "\n${YELLOW}[5/5] Installing frontend dependencies...${NC}"
cd frontend && npm install --silent && cd ..
echo -e "  ${GREEN}✓ Node modules installed${NC}"

echo -e "\n${GREEN}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  ✓ Setup complete!                                       ║"
echo "║                                                          ║"
echo "║  Start:    ./run.sh                                      ║"
echo "║  Frontend: http://localhost:3000                         ║"
echo "║  API Docs: http://localhost:8000/docs                    ║"
echo "║  CLI test: python scripts/test_search.py \"Andrew Ng\"    ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"
