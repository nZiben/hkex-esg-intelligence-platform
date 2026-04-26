from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Prediction
from app.schemas import PredictionRunResponse
from app.services.model_prediction import (
    PredictionInputError,
    PredictionModelUnavailable,
    predict_company_rating,
)

router = APIRouter(prefix="/api/v1", tags=["predictions"])


@router.post("/predictions/{stock_code}", response_model=PredictionRunResponse)
def run_company_prediction(stock_code: str, db: Session = Depends(get_db)) -> PredictionRunResponse:
    try:
        result = predict_company_rating(db, stock_code)
    except PredictionInputError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PredictionModelUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    prediction = Prediction(
        stock_code=result.stock_code,
        predicted_esg_rating=result.predicted_esg_rating,
        predicted_score=result.predicted_score,
        confidence=result.confidence,
        model_version=result.model_version,
        num_chunks=result.num_chunks,
        doc_count=result.doc_count,
    )
    db.add(prediction)
    db.commit()
    db.refresh(prediction)

    return PredictionRunResponse(
        stock_code=result.stock_code,
        company_name=result.company_name,
        predicted_esg_rating=result.predicted_esg_rating,
        predicted_score=result.predicted_score,
        confidence=result.confidence,
        model_version=result.model_version,
        num_chunks=result.num_chunks,
        doc_count=result.doc_count,
        run_at=prediction.run_at,
    )
