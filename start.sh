#!/bin/bash

echo "=========================================="
echo "  GESTURE CONTROL SYSTEM v2.0"
echo "=========================================="
echo ""

cd backend
python3 -m venv venv 2>/dev/null
source venv/bin/activate
pip install -r requirements.txt
python main.py &
BACKEND_PID=$!

echo "Backend started (PID: $BACKEND_PID)"
echo "Waiting for backend to initialize..."
sleep 5

cd ../frontend
npm install
npm start &
FRONTEND_PID=$!

echo ""
echo "=========================================="
echo "  Servers Started!"
echo "=========================================="
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo "WebSocket: ws://localhost:8000/ws"
echo ""
echo "Press Ctrl+C to stop all servers"
echo ""

trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT TERM
wait