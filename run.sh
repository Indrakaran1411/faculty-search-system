#!/bin/bash

# 1. Kill any existing processes on port 8000 (Backend) and 5173/5174 (Frontend)
echo "Cleaning up old processes..."
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:5173 | xargs kill -9 2>/dev/null

# 2. Start Backend
echo "Starting Backend..."
export PYTHONPATH=$PYTHONPATH:$(pwd)/backend
source venv/bin/activate
python backend/main.py &

# 3. Start Frontend
echo "Starting Frontend..."
cd frontend-vite
npm install # Good for your friend to have this
npm run dev &

echo "Both services are starting. Check the URLs above!"