.PHONY: backend frontend worker test smoke benchmark sweep phase migrate migrate-status

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

phase:
	PYTHONPATH=backend python -m app.simulation.sweep --phase

sweep:
	PYTHONPATH=backend python -m app.simulation.sweep

migrate:
	PYTHONPATH=backend python -m app.persistence.migrations upgrade

migrate-status:
	PYTHONPATH=backend python -m app.persistence.migrations status
