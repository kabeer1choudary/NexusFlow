VENV ?= .venv
PY := $(VENV)/bin/python
LOCK ?= requirements-dev.lock
COMPOSE ?= docker compose

.PHONY: up down migrate seed test lint fmt install locks lock-cli

install:
	python3 -m venv $(VENV)
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r $(LOCK) --require-hashes
	$(PY) -m pip install -r requirements-build.lock --require-hashes
	$(PY) -m pip install --no-deps --no-build-isolation -e .

locks:
	uv pip compile pyproject.toml --python-version 3.12 --universal --generate-hashes \
		-o requirements.lock
	uv pip compile pyproject.toml --extra dev --python-version 3.12 --universal \
		--generate-hashes -o requirements-dev.lock

lock-cli:
	cd cli && cargo generate-lockfile

up:
	$(COMPOSE) -f deploy/docker-compose.yml up -d --build

down:
	$(COMPOSE) -f deploy/docker-compose.yml down

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
