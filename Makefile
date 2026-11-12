VENV ?= .venv
PY := $(VENV)/bin/python

.PHONY: up down migrate seed test lint fmt install

install:
	python3 -m venv $(VENV)
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -e ".[dev]"

up:
	docker compose -f deploy/docker-compose.yml up -d --build

down:
	docker compose -f deploy/docker-compose.yml down

migrate:
	$(PY) -m alembic -c api/alembic.ini upgrade head

seed:
	$(PY) scripts/seed.py

test:
	$(PY) -m pytest

lint:
	$(PY) -m ruff check api/src tests scripts
	$(PY) -m mypy api/src

fmt:
	$(PY) -m ruff format api/src tests scripts
	$(PY) -m ruff check --fix api/src tests scripts
