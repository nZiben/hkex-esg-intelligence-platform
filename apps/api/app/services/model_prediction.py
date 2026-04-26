from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import sys

import joblib
import numpy as np
import torch
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Chunk, Company, Document

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from packages.ml.text_processing import chunk_text

SCORE_TO_RATING = [
    (91.7, "AAA"),
    (83.3, "AA+"),
    (75.0, "AA"),
    (66.7, "AA-"),
    (58.3, "A+"),
    (50.0, "A"),
    (41.7, "A-"),
    (33.3, "BBB+"),
    (25.0, "BBB"),
    (16.7, "BBB-"),
    (8.3, "BB+"),
    (0.0, "BB"),
]


class PredictionModelUnavailable(RuntimeError):
    pass


class PredictionInputError(ValueError):
    pass


class DeepRegressor(torch.nn.Module):
    def __init__(self, input_dim: int):
        super().__init__()
        self.net = torch.nn.Sequential(
            torch.nn.Linear(input_dim, 1024),
            torch.nn.BatchNorm1d(1024),
            torch.nn.ReLU(),
            torch.nn.Dropout(0.35),
            torch.nn.Linear(1024, 512),
            torch.nn.BatchNorm1d(512),
            torch.nn.ReLU(),
            torch.nn.Dropout(0.3),
            torch.nn.Linear(512, 256),
            torch.nn.BatchNorm1d(256),
            torch.nn.ReLU(),
            torch.nn.Dropout(0.25),
            torch.nn.Linear(256, 128),
            torch.nn.BatchNorm1d(128),
            torch.nn.ReLU(),
            torch.nn.Dropout(0.2),
            torch.nn.Linear(128, 64),
            torch.nn.ReLU(),
            torch.nn.Dropout(0.15),
            torch.nn.Linear(64, 32),
            torch.nn.ReLU(),
            torch.nn.Linear(32, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(-1)


@dataclass(frozen=True)
class ModelBundle:
    retriever: object
    predictor: torch.nn.Module
    scaler: object
    device: str


@dataclass(frozen=True)
class CompanyPrediction:
    stock_code: str
    company_name: str
    predicted_score: float
    predicted_esg_rating: str
    confidence: float
    model_version: str
    num_chunks: int
    doc_count: int


def score_to_rating(score: float) -> str:
    for threshold, rating in SCORE_TO_RATING:
        if score >= threshold:
            return rating
    return "BB"


def _model_paths() -> tuple[Path, Path, Path]:
    settings = get_settings()
    model_root = Path(settings.prediction_model_root)
    return (
        model_root / "retriever",
        model_root / "predictor" / "regression_head.pt",
        model_root / "predictor" / "scaler.pkl",
    )


@lru_cache(maxsize=1)
def load_model_bundle() -> ModelBundle:
    retriever_path, predictor_path, scaler_path = _model_paths()
    missing = [str(path) for path in [retriever_path, predictor_path, scaler_path] if not path.exists()]
    if missing:
        raise PredictionModelUnavailable(f"Prediction model artifacts are missing: {', '.join(missing)}")

    try:
        from sentence_transformers import SentenceTransformer
    except Exception as exc:  # pragma: no cover - dependency failure path
        raise PredictionModelUnavailable("sentence-transformers is required for ESG model prediction") from exc

    device = "cuda" if torch.cuda.is_available() else "cpu"
    retriever = SentenceTransformer(str(retriever_path), device=device)
    sample_emb = retriever.encode(["test"], convert_to_numpy=True, show_progress_bar=False)
    input_dim = int(sample_emb.shape[1])

    predictor = DeepRegressor(input_dim=input_dim).to(device)
    predictor.load_state_dict(torch.load(predictor_path, map_location=device))
    predictor.eval()

    scaler = joblib.load(scaler_path)
    return ModelBundle(retriever=retriever, predictor=predictor, scaler=scaler, device=device)


def _collect_prediction_chunks(db: Session, stock_code: str) -> tuple[Company, list[str], int]:
    normalized_code = stock_code.zfill(5)
    company = db.get(Company, normalized_code)
    if company is None:
        raise PredictionInputError("Company not found")

    documents = list(
        db.scalars(select(Document).where(Document.stock_code == normalized_code).order_by(Document.id)).all()
    )
    if not documents:
        raise PredictionInputError("No documents are available for this company")

    chunks = [
        text
        for (text,) in db.execute(
            select(Chunk.text)
            .join(Document, Chunk.document_id == Document.id)
            .where(Document.stock_code == normalized_code)
            .order_by(Document.id, Chunk.chunk_index)
        ).all()
        if text and len(text.strip()) > 50
    ]

    if not chunks:
        settings = get_settings()
        for doc in documents:
            chunks.extend(
                chunk
                for chunk in chunk_text(
                    doc.text_clean,
                    chunk_size=settings.chunk_size,
                    chunk_overlap=settings.chunk_overlap,
                )
                if len(chunk.strip()) > 50
            )

    if not chunks:
        raise PredictionInputError("No usable text chunks are available for this company")

    return company, chunks, len(documents)


def _confidence(num_chunks: int, doc_count: int) -> float:
    chunk_signal = min(num_chunks, 400) / 400
    doc_signal = min(doc_count, 4) / 4
    return round(max(0.55, min(0.9, 0.55 + chunk_signal * 0.30 + doc_signal * 0.05)), 3)


def predict_company_rating(db: Session, stock_code: str, bundle: ModelBundle | None = None) -> CompanyPrediction:
    settings = get_settings()
    company, chunks, doc_count = _collect_prediction_chunks(db, stock_code)
    active_bundle = bundle or load_model_bundle()

    chunks_to_encode = chunks[: settings.prediction_max_chunks]
    with torch.no_grad():
        embeddings = active_bundle.retriever.encode(
            chunks_to_encode,
            batch_size=settings.prediction_batch_size,
            convert_to_numpy=True,
            show_progress_bar=False,
        )

    embedding_matrix = np.asarray(embeddings, dtype=np.float32)
    if embedding_matrix.ndim != 2 or embedding_matrix.shape[0] == 0:
        raise PredictionInputError("Model did not produce valid embeddings")

    doc_embedding = embedding_matrix.mean(axis=0).reshape(1, -1)
    scaled = active_bundle.scaler.transform(doc_embedding)
    tensor = torch.tensor(scaled, dtype=torch.float32).to(active_bundle.device)

    active_bundle.predictor.eval()
    with torch.no_grad():
        score = active_bundle.predictor(tensor).detach().cpu().item()

    clipped_score = round(float(np.clip(score, 0, 100)), 1)
    return CompanyPrediction(
        stock_code=company.stock_code,
        company_name=company.company_name,
        predicted_score=clipped_score,
        predicted_esg_rating=score_to_rating(clipped_score),
        confidence=_confidence(len(chunks), doc_count),
        model_version=settings.prediction_model_version,
        num_chunks=len(chunks),
        doc_count=doc_count,
    )
