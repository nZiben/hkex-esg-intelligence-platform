from __future__ import annotations

import os
from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


EmbeddingType = JSON
if os.getenv("DATABASE_URL", "").startswith("postgresql"):
    try:
        from pgvector.sqlalchemy import Vector

        EmbeddingType = Vector(1536)
    except Exception:
        EmbeddingType = JSON


class Company(Base):
    __tablename__ = "companies"

    stock_code: Mapped[str] = mapped_column(String(12), primary_key=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    industry: Mapped[str | None] = mapped_column(String(255), nullable=True)
    esg_rating_raw: Mapped[str | None] = mapped_column(String(64), nullable=True)
    esg_rating_ordinal: Mapped[float | None] = mapped_column(Float, nullable=True)
    universe_ranking: Mapped[str | None] = mapped_column(String(64), nullable=True)
    peer_ranking: Mapped[str | None] = mapped_column(String(64), nullable=True)
    strengths: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    weaknesses: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    index_membership: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    documents: Mapped[list[Document]] = relationship(back_populates="company", cascade="all, delete-orphan")
    signal: Mapped[ESGSignal | None] = relationship(back_populates="company", uselist=False, cascade="all, delete-orphan")
    predictions: Mapped[list[Prediction]] = relationship(back_populates="company", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(ForeignKey("companies.stock_code", ondelete="CASCADE"), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(32), nullable=False)  # esg_report | annual_report
    source_file: Mapped[str] = mapped_column(String(512), nullable=False)
    report_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    text_clean: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    company: Mapped[Company] = relationship(back_populates="documents")
    chunks: Mapped[list[Chunk]] = relationship(back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("stock_code", "doc_type", "source_file", name="uq_document_source"),
        Index("ix_documents_stock_code", "stock_code"),
        Index("ix_documents_doc_type", "doc_type"),
    )


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(EmbeddingType, nullable=True)
    page_no: Mapped[int | None] = mapped_column(Integer, nullable=True)

    document: Mapped[Document] = relationship(back_populates="chunks")

    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_chunk_idx"),
        Index("ix_chunks_document_id", "document_id"),
    )


class ESGSignal(Base):
    __tablename__ = "esg_signals"

    stock_code: Mapped[str] = mapped_column(ForeignKey("companies.stock_code", ondelete="CASCADE"), primary_key=True)
    e_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    s_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    g_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    mixed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    esg_density: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    sentiment_pos: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    sentiment_neu: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    sentiment_neg: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    company: Mapped[Company] = relationship(back_populates="signal")


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(ForeignKey("companies.stock_code", ondelete="CASCADE"), nullable=False)
    predicted_esg_rating: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False, default="baseline-v1")
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    company: Mapped[Company] = relationship(back_populates="predictions")

    __table_args__ = (Index("ix_predictions_stock_run", "stock_code", "run_at"),)


class ChatLog(Base):
    __tablename__ = "chat_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    citations_json: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
