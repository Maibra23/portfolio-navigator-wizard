# Makefile for Portfolio Navigator Wizard

.PHONY: dev backend frontend prod-build prod-copy test-backend test-frontend

# Development: run both backend and frontend

dev:
	cd backend && source venv/bin/activate && uvicorn main:app --reload & \
	cd frontend && npm run dev

# Backend only
	cd backend && source venv/bin/activate && uvicorn main:app --reload

# Frontend only
frontend:
	cd frontend && npm run dev

# Production build: build frontend and copy to backend/static
prod-build:
	cd frontend && npm install && npm run build

prod-copy:
	cd frontend && npm run build && cp -r dist ../backend/static

# Backend tests
test-backend:
	cd backend && source venv/bin/activate && pytest

# Frontend tests
test-frontend:
	cd frontend && npm test 