from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EvalResult:
    topic_macro_f1: float
    prediction_mae: float
    citation_coverage: float
    groundedness: float
    p95_latency_s: float


def passes_thresholds(result: EvalResult) -> dict[str, bool]:
    return {
        "topic_macro_f1": result.topic_macro_f1 >= 0.78,
        "prediction_mae": result.prediction_mae <= 1.0,
        "citation_coverage": result.citation_coverage >= 0.95,
        "groundedness": result.groundedness >= 0.85,
        "p95_latency_s": result.p95_latency_s <= 8.0,
    }
