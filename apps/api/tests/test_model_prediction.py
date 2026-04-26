from __future__ import annotations

import numpy as np
import pytest
import torch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.models import Base, Chunk, Company, Document
from app.services.model_prediction import (
    ModelBundle,
    PredictionInputError,
    PredictionModelUnavailable,
    load_model_bundle,
    predict_company_rating,
    score_to_rating,
)
from scripts.bootstrap_ingest import remove_chinese_characters


class FakeRetriever:
    def encode(self, texts, **kwargs):
        return np.ones((len(texts), 3), dtype=np.float32)


class FakeScaler:
    def transform(self, matrix):
        return matrix


class FakePredictor(torch.nn.Module):
    def forward(self, tensor):
        return torch.tensor([54.2], dtype=torch.float32, device=tensor.device)


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def test_score_to_rating() -> None:
    assert score_to_rating(95.0) == "AAA"
    assert score_to_rating(54.2) == "A"
    assert score_to_rating(4.0) == "BB"


def test_missing_model_artifacts_raise(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("PREDICTION_MODEL_ROOT", str(tmp_path))
    get_settings.cache_clear()
    load_model_bundle.cache_clear()

    with pytest.raises(PredictionModelUnavailable):
        load_model_bundle()

    get_settings.cache_clear()
    load_model_bundle.cache_clear()


def test_no_documents_raise_input_error(db_session) -> None:
    db_session.add(Company(stock_code="00001", company_name="Empty Co"))
    db_session.commit()

    with pytest.raises(PredictionInputError):
        predict_company_rating(db_session, "00001", bundle=_fake_bundle())


def test_prediction_with_mocked_models(db_session) -> None:
    company = Company(stock_code="00001", company_name="CKH HOLDINGS")
    db_session.add(company)
    db_session.flush()

    document = Document(
        stock_code="00001",
        doc_type="annual_report",
        source_file="00001.pdf",
        text_clean="Governance and climate reporting content " * 20,
    )
    db_session.add(document)
    db_session.flush()
    db_session.add(
        Chunk(
            document_id=document.id,
            chunk_index=0,
            text="Governance and climate reporting content with enough length for prediction." * 2,
        )
    )
    db_session.commit()

    result = predict_company_rating(db_session, "1", bundle=_fake_bundle())

    assert result.stock_code == "00001"
    assert result.company_name == "CKH HOLDINGS"
    assert result.predicted_score == 54.2
    assert result.predicted_esg_rating == "A"
    assert result.num_chunks == 1
    assert result.doc_count == 1


def test_remove_chinese_characters() -> None:
    assert remove_chinese_characters("Board 董事會 climate 氣候 risk") == "Board  climate  risk"


def _fake_bundle() -> ModelBundle:
    return ModelBundle(
        retriever=FakeRetriever(),
        predictor=FakePredictor(),
        scaler=FakeScaler(),
        device="cpu",
    )
