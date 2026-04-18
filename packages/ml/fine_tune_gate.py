from __future__ import annotations

from pathlib import Path

from packages.ml.evaluate import EvalResult, passes_thresholds


def should_fine_tune(eval_result: EvalResult) -> tuple[bool, list[str]]:
    checks = passes_thresholds(eval_result)
    failing = [name for name, passed in checks.items() if not passed]
    return (len(failing) > 0, failing)


def fine_tune_plan(failing_metrics: list[str]) -> list[str]:
    steps = []
    if any(m in failing_metrics for m in ["citation_coverage", "groundedness"]):
        steps.append(
            "Run retriever triplet fine-tuning: python scripts/run_retriever_finetune.py --data-dir data --epochs 1"
        )
    if any(m in failing_metrics for m in ["topic_macro_f1", "prediction_mae"]):
        steps.append("Increase labeled ESG training set and recalibrate supervised models.")
    if len(failing_metrics) >= 3:
        steps.append("Run optional LoRA fine-tuning for response style and domain grounding.")
    return steps or ["No fine-tuning required."]


def finetune_artifact_status(base_dir: str = "artifacts/finetuned-retriever") -> dict[str, str | bool]:
    root = Path(base_dir)
    model_exists = root.exists() and any(root.iterdir())
    report_path = root / "finetune_report.json"
    return {
        "model_dir": str(root),
        "model_exists": model_exists,
        "report_exists": report_path.exists(),
        "report_path": str(report_path),
    }
