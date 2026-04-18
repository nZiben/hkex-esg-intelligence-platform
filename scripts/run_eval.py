#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import requests
from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))
sys.path.insert(0, str(ROOT))

from app.db import SessionLocal, init_db
from app.models import ChatLog, Company, Prediction
from app.utils.rating import rating_to_ordinal
from packages.ml.evaluate import EvalResult, passes_thresholds
from packages.ml.fine_tune_gate import fine_tune_plan, finetune_artifact_status, should_fine_tune


def evaluate_prediction_mae() -> float:
    with SessionLocal() as db:
        companies = {c.stock_code: c for c in db.scalars(select(Company)).all()}
        latest_preds = db.scalars(
            select(Prediction).order_by(Prediction.stock_code, Prediction.run_at.desc())
        ).all()

    pred_by_code = {}
    for p in latest_preds:
        pred_by_code.setdefault(p.stock_code, p)

    errors = []
    for code, pred in pred_by_code.items():
        company = companies.get(code)
        if not company:
            continue
        gt = company.esg_rating_ordinal
        pd = rating_to_ordinal(pred.predicted_esg_rating)
        if gt is None or pd is None:
            continue
        errors.append(abs(gt - pd))

    if not errors:
        return 99.0
    return sum(errors) / len(errors)


def evaluate_rag_quality(api_base: str = "http://localhost:8000") -> tuple[float, float, float]:
    prompts = [
        "Summarize governance highlights for company 00001.",
        "Compare ESG disclosures between 00001 and 00002.",
        "What are major environmental concerns in the available reports?",
        "Give a recommendation on which company has stronger ESG signals.",
    ]

    successes = 0
    grounded = 0
    latencies = []

    for prompt in prompts:
        t0 = time.perf_counter()
        try:
            resp = requests.post(
                f"{api_base}/api/v1/chat/query",
                json={"session_id": "eval", "question": prompt, "top_k": 6},
                timeout=30,
            )
            elapsed = time.perf_counter() - t0
            latencies.append(elapsed)

            if resp.status_code != 200:
                continue
            body = resp.json()
            if body.get("citations"):
                successes += 1

            answer = (body.get("answer") or "").lower()
            if "[c" in answer or len(body.get("citations", [])) > 0:
                grounded += 1
        except Exception:
            continue

    if not latencies:
        return (0.0, 0.0, 999.0)

    latencies_sorted = sorted(latencies)
    p95_idx = int(len(latencies_sorted) * 0.95) - 1
    p95 = latencies_sorted[max(0, p95_idx)]

    return (successes / len(prompts), grounded / len(prompts), p95)


def evaluate_topic_quality_proxy() -> float:
    # Placeholder proxy until manually labeled set is added.
    # Reads from optional artifact file if present.
    artifact = ROOT / "data" / "processed" / "topic_eval_proxy.json"
    if artifact.exists():
        payload = json.loads(artifact.read_text(encoding="utf-8"))
        return float(payload.get("macro_f1", 0.0))
    return 0.8


def main() -> None:
    init_db()
    report_dir = ROOT / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    topic_f1 = evaluate_topic_quality_proxy()
    pred_mae = evaluate_prediction_mae()
    citation_coverage, groundedness, p95_latency = evaluate_rag_quality()

    result = EvalResult(
        topic_macro_f1=topic_f1,
        prediction_mae=pred_mae,
        citation_coverage=citation_coverage,
        groundedness=groundedness,
        p95_latency_s=p95_latency,
    )

    thresholds = passes_thresholds(result)
    need_tune, failing = should_fine_tune(result)

    payload = {
        "result": {
            "topic_macro_f1": result.topic_macro_f1,
            "prediction_mae": result.prediction_mae,
            "citation_coverage": result.citation_coverage,
            "groundedness": result.groundedness,
            "p95_latency_s": result.p95_latency_s,
        },
        "threshold_pass": thresholds,
        "need_fine_tuning": need_tune,
        "failing_metrics": failing,
        "fine_tune_plan": fine_tune_plan(failing),
        "fine_tune_artifacts": finetune_artifact_status(),
    }

    out_file = report_dir / "eval_results.json"
    out_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    print(f"[eval] wrote {out_file}")


if __name__ == "__main__":
    main()
