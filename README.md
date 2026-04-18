# Project 7 ESG Chatbot (Business Sector)

End-to-end ESG intelligence platform for HKEX companies with:
- RAG chatbot with citations
- ESG dashboard and company comparison UI
- NLP/data mining pipeline for keywords, topics, sentiment, and ESG score prediction

## Repository Layout

- `apps/web`: Next.js UI (`/chat`, `/dashboard`, `/company/[stock_code]`, `/compare`)
- `apps/api`: FastAPI backend and REST APIs
- `packages/ml`: NLP/data mining and model training/evaluation modules
- `scripts`: ingestion, evaluation, report artifact generation
- `infra`: deployment templates for Vercel, Render, Supabase
- `data`: project input archives (`JSON`, `PDFS`, `PDFS_2`)

## Data Setup (Important)

If your local `data/` folder is empty, download the project dataset archives first and place them in:

- `data/`

Expected archive naming/prefixes:

- `JSON*.zip`
- `PDFS*.zip`
- `PDFS_2*.zip`

Then run ingestion:

```bash
python scripts/bootstrap_ingest.py --data-dir data
```

Quick check before ingestion:

```bash
ls -lh data
```

## Quick Start

1. Copy env file:

```bash
cp .env.example .env
```

2. Install Python deps:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r apps/api/requirements.txt
```

3. Install web deps:

```bash
cd apps/web && npm install
```

4. Run ingest bootstrap:

```bash
python scripts/bootstrap_ingest.py --data-dir data
```

5. Run backend and frontend:

```bash
make api
make web
```

## API Endpoints

- `POST /api/v1/chat/query`
- `GET /api/v1/companies`
- `GET /api/v1/companies/{stock_code}/profile`
- `GET /api/v1/companies/{stock_code}/signals`
- `GET /api/v1/compare?codes=00001,00002`
- `GET /api/v1/dashboard/overview`

## Evaluation Gates

Run:

```bash
python scripts/run_eval.py
```

Default target thresholds:
- Topic macro-F1 `>= 0.78`
- ESG prediction MAE `<= 1.0`
- Citation coverage `>= 0.95`
- Groundedness `>= 0.85`
- p95 latency `<= 8s`

If gates fail, use `packages/ml/fine_tune_gate.py` to trigger retriever/reranker hard-negative training, then optional LoRA workflow.

## Real Fine-Tuning (Optional, but implemented)

This repo includes a **real retriever fine-tuning pipeline** (triplet loss, not a mock):

```bash
python scripts/run_retriever_finetune.py --data-dir data --epochs 1
```

What it does:
- Builds triplets from ESG data (DB chunks if available, otherwise `JSON*.zip` fallback)
- Fine-tunes `sentence-transformers/all-MiniLM-L6-v2` using triplet loss
- Saves model checkpoint and a training report

Artifacts produced:
- `artifacts/finetuned-retriever/retriever_triplets.jsonl`
- `artifacts/finetuned-retriever/` (model files)
- `artifacts/finetuned-retriever/finetune_report.json`

You can verify training status via:

```bash
python scripts/run_eval.py
```

and inspect `fine_tune_artifacts` in `reports/eval_results.json`.
