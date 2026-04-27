from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class OrmBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Citation(BaseModel):
    citation_id: str
    stock_code: str
    company_name: str | None = None
    doc_type: str
    source_file: str
    page_no: int | None = None
    snippet: str


class ChatQueryRequest(BaseModel):
    session_id: str = Field(default="default-session")
    question: str
    stock_codes: list[str] | None = None
    top_k: int = Field(default=8, ge=1, le=20)


class ChatQueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
    confidence: float
    latency_ms: int
    follow_up_questions: list[str]


class CompanySummary(OrmBaseModel):
    stock_code: str
    company_name: str
    industry: str | None
    esg_rating_raw: str | None
    esg_rating_ordinal: float | None


class ESGSignalOut(OrmBaseModel):
    stock_code: str
    e_count: int
    s_count: int
    g_count: int
    mixed_count: int
    esg_density: float
    sentiment_pos: float
    sentiment_neu: float
    sentiment_neg: float


class PredictionOut(OrmBaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    predicted_esg_rating: str
    predicted_score: float | None = None
    confidence: float
    model_version: str
    num_chunks: int | None = None
    doc_count: int | None = None
    run_at: datetime


class PredictionRunResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    stock_code: str
    company_name: str
    predicted_esg_rating: str
    predicted_score: float
    confidence: float
    model_version: str
    num_chunks: int
    doc_count: int
    run_at: datetime


class AuxiliaryPredictionKind(str, Enum):
    all = "all"
    topics = "topics"
    themes = "themes"
    sentiment = "sentiment"


class TopicPredictionOut(BaseModel):
    label: str
    probability: float
    predicted: bool


class ThemePredictionOut(BaseModel):
    theme: str
    mentions: int
    share: float


class SentimentPredictionOut(BaseModel):
    pillar: str
    sentiment: str
    positive_similarity: float
    negative_similarity: float
    margin: float


class AuxiliaryPredictionRunResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    stock_code: str
    company_name: str
    prediction_type: AuxiliaryPredictionKind
    model_version: str
    num_chunks: int
    doc_count: int
    run_at: datetime
    topics: list[TopicPredictionOut] = Field(default_factory=list)
    themes: list[ThemePredictionOut] = Field(default_factory=list)
    sentiment: list[SentimentPredictionOut] = Field(default_factory=list)


class CompanyProfileResponse(BaseModel):
    company: CompanySummary
    strengths: list[str] = []
    weaknesses: list[str] = []
    index_membership: list[str] = []
    top_keywords: list[str] = []
    signal: ESGSignalOut | None = None
    latest_prediction: PredictionOut | None = None


class CompareCompanyCard(BaseModel):
    stock_code: str
    company_name: str
    esg_rating_raw: str | None
    esg_density: float | None
    dominant_topic: str | None
    sentiment_balance: float | None


class CompareResponse(BaseModel):
    companies: list[CompareCompanyCard]
    recommendation_summary: str


class DashboardOverviewResponse(BaseModel):
    company_count: int
    industry_distribution: dict[str, int]
    avg_esg_density: float
    topic_totals: dict[str, int]
    sentiment_totals: dict[str, float]
    top_companies_by_density: list[CompanySummary]
