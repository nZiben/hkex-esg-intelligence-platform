from __future__ import annotations

from packages.ml.evaluate import EvalResult, passes_thresholds


def should_fine_tune(eval_result: EvalResult) -> tuple[bool, list[str]]:
    checks = passes_thresholds(eval_result)
    failing = [name for name, passed in checks.items() if not passed]
    return (len(failing) > 0, failing)


def fine_tune_plan(failing_metrics: list[str]) -> list[str]:
    steps = []
    if any(m in failing_metrics for m in ["citation_coverage", "groundedness"]):
        steps.append("Run retriever/reranker hard-negative training on mis-grounded QA pairs.")
    if any(m in failing_metrics for m in ["topic_macro_f1", "prediction_mae"]):
        steps.append("Increase labeled ESG training set and recalibrate supervised models.")
    if len(failing_metrics) >= 3:
        steps.append("Run optional LoRA fine-tuning for response style and domain grounding.")
    return steps or ["No fine-tuning required."]
