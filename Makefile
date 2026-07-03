.PHONY: backend frontend worker test smoke benchmark migrate migrate-status

backend:
	uvicorn app.main:app --reload --app-dir backend

frontend:
	npm --prefix frontend run dev

worker:
	PYTHONPATH=backend python -m app.worker

test:
	PYTHONPATH=backend pytest backend/tests

smoke:
	PYTHONPATH=backend python -m app.simulation.smoke

benchmark:
	PYTHONPATH=backend python -m app.simulation.benchmark

migrate:
	PYTHONPATH=backend python -m app.persistence.migrations upgrade

migrate-status:
	PYTHONPATH=backend python -m app.persistence.migrations status
