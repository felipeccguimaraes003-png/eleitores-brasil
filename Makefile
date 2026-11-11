PY ?= python

.PHONY: install lint typecheck arch security test check run-api run-frontend up smoke

install:
	$(PY) -m pip install -r requirements-dev.txt

lint:
	ruff check . && ruff format --check .

typecheck:
	mypy

arch:
	lint-imports

security:
	bandit -q -r backend frontend scripts -ll

test:
	pytest

check: lint typecheck arch security test  ## tudo o que o CI roda (exceto auditoria e Docker)

run-api:
	uvicorn backend.main:app --reload --port 8000

run-frontend:
	PYTHONPATH=. API_BASE_URL=http://localhost:8000 streamlit run frontend/streamlit_app.py

up:
	docker compose up --build

smoke:
	$(PY) scripts/smoke_sources.py
