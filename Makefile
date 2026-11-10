.PHONY: up down logs build test lint

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f app

build:
	docker compose build

test:
	pytest -q

lint:
	python -m compileall app