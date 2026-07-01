.PHONY: setup dev test lint build clean

setup:
	@echo "🚀 Setting up BestPriceToday..."
	cp backend/.env.example backend/.env
	cp frontend/.env.example frontend/.env.local
	cd backend && python -m venv venv && . venv/bin/activate && pip install -r requirements.txt
	cd frontend && npm install
	@echo "✅ Setup complete! Edit backend/.env and run: make dev"

dev:
	docker compose up --build

dev-backend:
	cd backend && . venv/bin/activate && uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

dev-bot:
	cd backend && . venv/bin/activate && python -m app.workers.bestprice_bot

test:
	cd backend && . venv/bin/activate && pytest tests -v

lint:
	cd backend && . venv/bin/activate && ruff check app && black --check app
	cd frontend && npm run lint

format:
	cd backend && . venv/bin/activate && black app && ruff check --fix app

migrate:
	cd backend && . venv/bin/activate && alembic upgrade head

migration:
	cd backend && . venv/bin/activate && alembic revision --autogenerate -m "$(name)"

build:
	docker compose build

clean:
	docker compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -name "*.pyc" -delete
