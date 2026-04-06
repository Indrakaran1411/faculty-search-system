#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# Faculty Information Retrieval System — Start Script
# Launches both backend (port 8000) and frontend (port 3000)
# ─────────────────────────────────────────────────────────────────────────────

GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; NC='\033[0m'

# Activate virtualenv if present
if [ -d "venv" ]; then
  source venv/bin/activate
else
  echo -e "${YELLOW}⚠ venv not found — run ./setup.sh first${NC}"
  exit 1
fi

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════╗"
echo "║   Faculty Search System — Starting...            ║"
echo "╚══════════════════════════════════════════════════╝"
echo -e "${NC}"

# ── Start backend ─────────────────────────────────────────────────────────────
echo -e "${GREEN}▶ Starting backend  →  http://localhost:8000${NC}"
cd backend
python main.py &
BACKEND_PID=$!
cd ..

# Give backend a moment to initialise
sleep 2

# ── Start frontend ────────────────────────────────────────────────────────────
echo -e "${GREEN}▶ Starting frontend →  http://localhost:3000${NC}"
cd frontend
npm start &
FRONTEND_PID=$!
cd ..

echo ""
echo -e "${GREEN}Both services running."
echo "  Frontend : http://localhost:3000"
echo "  Backend  : http://localhost:8000"
echo "  API Docs : http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both."
echo -e "${NC}"

# Graceful shutdown
trap "echo 'Stopping...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM
wait
