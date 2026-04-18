.PHONY: help api web ingest eval report finetune test-api lint

help:
	@echo "Targets:"
	@echo "  api      - Run FastAPI backend"
	@echo "  web      - Run Next.js frontend"
	@echo "  ingest   - Run bootstrap ingestion pipeline"
	@echo "  eval     - Run evaluation suite"
	@echo "  finetune - Run real retriever fine-tuning pipeline"
	@echo "  report   - Generate report charts/csv artifacts"
	@echo "  test-api - Run backend tests"

api:
	cd apps/api && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

web:
	cd apps/web && npm run dev

ingest:
	python scripts/bootstrap_ingest.py --data-dir data

eval:
	python scripts/run_eval.py

finetune:
	python scripts/run_retriever_finetune.py --data-dir data --epochs 1

report:
	python scripts/generate_report_artifacts.py

test-api:
	cd apps/api && pytest -q
