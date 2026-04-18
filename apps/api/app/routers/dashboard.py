from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Company, ESGSignal
from app.schemas import CompareCompanyCard, CompareResponse, CompanySummary, DashboardOverviewResponse

router = APIRouter(prefix="/api/v1", tags=["dashboard"])


@router.get("/dashboard/overview", response_model=DashboardOverviewResponse)
def dashboard_overview(db: Session = Depends(get_db)) -> DashboardOverviewResponse:
    companies = db.scalars(select(Company)).all()
    if not companies:
        return DashboardOverviewResponse(
            company_count=0,
            industry_distribution={},
            avg_esg_density=0.0,
            topic_totals={"E": 0, "S": 0, "G": 0, "Mixed": 0},
            sentiment_totals={"positive": 0.0, "neutral": 0.0, "negative": 0.0},
            top_companies_by_density=[],
        )

    industry_counts = Counter([c.industry or "Unknown" for c in companies])

    signals = db.scalars(select(ESGSignal)).all()
    avg_density = sum(s.esg_density for s in signals) / max(len(signals), 1)

    topic_totals = {
        "E": sum(s.e_count for s in signals),
        "S": sum(s.s_count for s in signals),
        "G": sum(s.g_count for s in signals),
        "Mixed": sum(s.mixed_count for s in signals),
    }
    sentiment_totals = {
        "positive": sum(s.sentiment_pos for s in signals),
        "neutral": sum(s.sentiment_neu for s in signals),
        "negative": sum(s.sentiment_neg for s in signals),
    }

    top_density_companies = db.scalars(
        select(Company)
        .join(ESGSignal, Company.stock_code == ESGSignal.stock_code)
        .order_by(desc(ESGSignal.esg_density))
        .limit(5)
    ).all()

    return DashboardOverviewResponse(
        company_count=len(companies),
        industry_distribution=dict(industry_counts),
        avg_esg_density=round(avg_density, 4),
        topic_totals=topic_totals,
        sentiment_totals=sentiment_totals,
        top_companies_by_density=[
            CompanySummary(
                stock_code=c.stock_code,
                company_name=c.company_name,
                industry=c.industry,
                esg_rating_raw=c.esg_rating_raw,
                esg_rating_ordinal=c.esg_rating_ordinal,
            )
            for c in top_density_companies
        ],
    )


@router.get("/compare", response_model=CompareResponse)
def compare_companies(codes: str = Query(..., description="Comma-separated stock codes"), db: Session = Depends(get_db)) -> CompareResponse:
    code_list = [c.strip() for c in codes.split(",") if c.strip()]
    if len(code_list) < 2:
        raise HTTPException(status_code=400, detail="Provide at least two stock codes")

    cards: list[CompareCompanyCard] = []
    for code in code_list:
        company = db.get(Company, code)
        if not company:
            continue
        signal = db.get(ESGSignal, code)

        dominant_topic = None
        sentiment_balance = None
        density = None
        if signal:
            topic_counts = {
                "E": signal.e_count,
                "S": signal.s_count,
                "G": signal.g_count,
                "Mixed": signal.mixed_count,
            }
            dominant_topic = max(topic_counts, key=topic_counts.get)
            sentiment_balance = signal.sentiment_pos - signal.sentiment_neg
            density = signal.esg_density

        cards.append(
            CompareCompanyCard(
                stock_code=company.stock_code,
                company_name=company.company_name,
                esg_rating_raw=company.esg_rating_raw,
                esg_density=density,
                dominant_topic=dominant_topic,
                sentiment_balance=sentiment_balance,
            )
        )

    if not cards:
        raise HTTPException(status_code=404, detail="No matching companies found")

    best = sorted(cards, key=lambda c: (c.esg_density or 0.0), reverse=True)[0]
    recommendation = (
        f"{best.company_name} ({best.stock_code}) currently shows the strongest ESG disclosure density in this set. "
        "Use chat view to inspect citation-backed evidence before final recommendation."
    )

    return CompareResponse(companies=cards, recommendation_summary=recommendation)
