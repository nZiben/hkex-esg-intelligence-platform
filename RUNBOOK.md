# Runbook

## Local startup

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -r apps/api/requirements.txt
cd apps/web && npm install && cd ../..
python scripts/bootstrap_ingest.py --data-dir data --max-pdfs 50 --skip-embeddings
```

Terminal A:

```bash
make api
```

Terminal B:

```bash
make web
```

## Evaluation

```bash
python scripts/run_eval.py
python scripts/generate_report_artifacts.py
```

## Fine-tuning (real retriever training)

```bash
python scripts/run_retriever_finetune.py --data-dir data --epochs 1
```

Output:
- `artifacts/finetuned-retriever/retriever_triplets.jsonl`
- `artifacts/finetuned-retriever/finetune_report.json`

## On-demand ESG prediction

Model artifacts live under local `models/` and are intentionally ignored by Git. Copy `models/retriever/` and `models/predictor/` from the teammate handoff folder, and keep `models/topic_classifier/classifier.pt` from the topic training run before using the prediction workflows.

Start the API, then run:

```bash
curl -X POST http://localhost:8000/api/v1/predictions/00001
curl -X POST "http://localhost:8000/api/v1/predictions/00001/insights?kind=all"
```

Use the web page at `/predictions` to run the same workflows from the UI. Select one company, use `Run Rating` for the ESG grade, or select a signal mode and click its run button.

## Submission artifacts

- `reports/eval_results.json`
- `reports/chapter4_company_signals.csv`
- `reports/chapter4_topic_distribution.png`
- `reports/chapter4_esg_density_hist.png`
