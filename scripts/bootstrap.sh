#!/bin/bash
# Bootstrap script for Linux — sets up everything from scratch
set -e

echo "🚀 BestPriceToday Bootstrap"
echo "================================"

# Check deps
command -v docker >/dev/null || { echo "❌ Docker not found. Install: https://docs.docker.com/engine/install/"; exit 1; }
command -v node >/dev/null || { echo "❌ Node.js not found. Install: https://nodejs.org"; exit 1; }
command -v python3 >/dev/null || { echo "❌ Python 3 not found."; exit 1; }

echo "✅ Dependencies OK"

# Copy env files
[ -f backend/.env ] || cp backend/.env.example backend/.env
[ -f frontend/.env.local ] || cp frontend/.env.example frontend/.env.local

echo "📋 .env files created — EDIT backend/.env with your API keys!"

# Setup Python venv
python3 -m venv backend/venv
source backend/venv/bin/activate
pip install -r backend/requirements.txt -q

echo "🐍 Python venv ready"

# Setup Node
cd frontend && npm install --silent && cd ..

echo "⚛️  Node modules installed"

echo ""
echo "================================"
echo "✅ Bootstrap complete!"
echo ""
echo "Next steps:"
echo "  1. Edit backend/.env with your API keys"
echo "  2. Run: make dev (Docker) or make dev-backend + make dev-frontend"
echo "  3. Access: http://localhost:3000"
echo "  4. API docs: http://localhost:8000/docs"
