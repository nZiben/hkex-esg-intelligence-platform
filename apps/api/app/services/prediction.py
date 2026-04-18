from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.ensemble import RandomForestRegressor

from app.utils.rating import ordinal_to_rating


@dataclass
class PredictionResult:
    rating: str
    confidence: float
    raw_score: float


def train_regressor(features: np.ndarray, targets: np.ndarray) -> RandomForestRegressor:
    model = RandomForestRegressor(
        n_estimators=200,
        max_depth=8,
        random_state=42,
    )
    model.fit(features, targets)
    return model


def baseline_predict(e_count: int, s_count: int, g_count: int, density: float) -> PredictionResult:
    # Governance-heavy disclosures often dominate in this dataset; keep weighted blend explicit.
    total = max(e_count + s_count + g_count, 1)
    composition = (e_count / total) * 0.35 + (s_count / total) * 0.25 + (g_count / total) * 0.40
    score = 4.8 + 3.8 * composition + 2.0 * min(max(density, 0.0), 1.0)
    rating = ordinal_to_rating(score)
    confidence = float(max(0.5, min(0.9, 0.55 + (density * 0.35))))
    return PredictionResult(rating=rating, confidence=confidence, raw_score=score)
