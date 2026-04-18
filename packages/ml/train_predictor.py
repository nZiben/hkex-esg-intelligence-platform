from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split

from app.services.prediction import train_regressor
from app.utils.rating import rating_to_ordinal


@dataclass
class TrainResult:
    model_path: str
    mae: float
    sample_size: int


def train_rating_model(records: list[dict], model_dir: str = "artifacts") -> TrainResult:
    features = []
    targets = []

    for rec in records:
        rating = rating_to_ordinal(rec.get("esg_rating_raw"))
        if rating is None:
            continue
        vector = np.array(rec["feature_vector"], dtype=float)
        features.append(vector)
        targets.append(rating)

    if len(features) < 8:
        raise ValueError("Not enough labeled records to train ESG rating model.")

    X = np.vstack(features)
    y = np.array(targets)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = train_regressor(X_train, y_train)
    preds = model.predict(X_test)
    mae = float(mean_absolute_error(y_test, preds))

    out_dir = Path(model_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    model_path = out_dir / "esg_rating_regressor.joblib"
    joblib.dump(model, model_path)

    with (out_dir / "esg_rating_metrics.json").open("w", encoding="utf-8") as f:
        json.dump({"mae": mae, "samples": len(features)}, f, indent=2)

    return TrainResult(model_path=str(model_path), mae=mae, sample_size=len(features))
