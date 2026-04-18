from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Chunk, Company, Document, ESGSignal, Prediction
from app.schemas import CompanyProfileResponse, CompanySummary, ESGSignalOut, PredictionOut
from app.services.nlp import extract_top_keywords

router = APIRouter(prefix="/api/v1", tags=["companies"])


@router.get("/companies", response_model=list[CompanySummary])
def list_companies(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[CompanySummary]:
    rows = db.scalars(select(Company).order_by(Company.stock_code).limit(limit).offset(offset)).all()
    return [
        CompanySummary(
            stock_code=row.stock_code,
            company_name=row.company_name,
            industry=row.industry,
            esg_rating_raw=row.esg_rating_raw,
            esg_rating_ordinal=row.esg_rating_ordinal,
        )
        for row in rows
    ]


@router.get("/companies/{stock_code}/profile", response_model=CompanyProfileResponse)
def get_company_profile(stock_code: str, db: Session = Depends(get_db)) -> CompanyProfileResponse:
    company = db.get(Company, stock_code)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    signal = db.get(ESGSignal, stock_code)

    latest_prediction = db.scalars(
        select(Prediction).where(Prediction.stock_code == stock_code).order_by(desc(Prediction.run_at)).limit(1)
    ).first()

    texts = db.scalars(
        select(Chunk.text)
        .join(Document, Chunk.document_id == Document.id)
        .where(Document.stock_code == stock_code)
        .limit(600)
    ).all()
    top_keywords = extract_top_keywords(list(texts), top_n=12)

    return CompanyProfileResponse(
        company=CompanySummary(
            stock_code=company.stock_code,
            company_name=company.company_name,
            industry=company.industry,
            esg_rating_raw=company.esg_rating_raw,
            esg_rating_ordinal=company.esg_rating_ordinal,
        ),
        strengths=company.strengths or [],
        weaknesses=company.weaknesses or [],
        index_membership=company.index_membership or [],
        top_keywords=top_keywords,
        signal=ESGSignalOut.model_validate(signal) if signal else None,
        latest_prediction=PredictionOut.model_validate(latest_prediction) if latest_prediction else None,
    )


@router.get("/companies/{stock_code}/signals", response_model=ESGSignalOut)
def get_company_signals(stock_code: str, db: Session = Depends(get_db)) -> ESGSignalOut:
    signal = db.get(ESGSignal, stock_code)
    if not signal:
        raise HTTPException(status_code=404, detail="Signals not found for company")
    return ESGSignalOut.model_validate(signal)
