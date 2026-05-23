frontend-deps:
	cd ./frontend && npm install --legacy-peer-deps

build-frontend:
	cd ./frontend && npm run build

run:
	docker compose up

up:
	docker compose up

build:
	docker compose build

seed-funds:
	docker compose up -d mongo api
	docker compose exec api python -m migrations.seed_funds

test:
	docker compose exec api pytest --cov --cov-report=term-missing --cov-report=html:htmlcov

test-fast:
	docker compose exec api pytest -x --tb=short

test-coverage:
	docker compose exec api pytest --cov --cov-report=term --cov-report=xml --cov-fail-under=70

.PHONY: frontend-deps build-frontend run up build seed-funds test test-fast test-coverage
