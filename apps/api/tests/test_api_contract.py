from __future__ import annotations

import os
from pathlib import Path

from fastapi.testclient import TestClient


os.environ["DATABASE_URL"] = "sqlite:///./test_api_contract.db"

from app.db import SessionLocal, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Chunk, Company, Document, ESGSignal  # noqa: E402
from app.utils.rating import rating_to_ordinal  # noqa: E402


def setup_module() -> None:
    db_path = Path("test_api_contract.db")
    if db_path.exists():
        db_path.unlink()
    init_db()

    with SessionLocal() as db:
        company = Company(
            stock_code="00001",
            company_name="CKH HOLDINGS",
            industry="Conglomerates",
            esg_rating_raw="AA+",
            esg_rating_ordinal=rating_to_ordinal("AA+"),
            strengths=["Corporate Governance"],
            weaknesses=[],
            index_membership=["HSI ESG Index"],
        )
        db.add(company)
        db.flush()

        doc = Document(
            stock_code="00001",
            doc_type="esg_report",
            source_file="00001.pdf",
            report_year=2025,
            text_clean="Board audit committee improved risk governance and energy management.",
        )
        db.add(doc)
        db.flush()

        chunk = Chunk(
            document_id=doc.id,
            chunk_index=0,
            text="The board and audit committee improved governance risk controls while reducing energy waste.",
            embedding=[0.1, 0.2, 0.3, 0.4],
            page_no=4,
        )
        db.add(chunk)

        signal = ESGSignal(
            stock_code="00001",
            e_count=20,
            s_count=12,
            g_count=48,
            mixed_count=7,
            esg_density=0.42,
            sentiment_pos=0.58,
            sentiment_neu=0.31,
            sentiment_neg=0.11,
        )
        db.add(signal)
        db.commit()


client = TestClient(app)


def test_health() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_list_companies() -> None:
    resp = client.get("/api/v1/companies")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert body[0]["stock_code"] == "00001"


def test_company_profile() -> None:
    resp = client.get("/api/v1/companies/00001/profile")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["company"]["stock_code"] == "00001"
    assert "top_keywords" in payload


def test_company_signals() -> None:
    resp = client.get("/api/v1/companies/00001/signals")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["g_count"] == 48


def test_dashboard_overview() -> None:
    resp = client.get("/api/v1/dashboard/overview")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["company_count"] >= 1


def test_compare() -> None:
    resp = client.get("/api/v1/compare", params={"codes": "00001,00001"})
    assert resp.status_code == 200
    payload = resp.json()
    assert len(payload["companies"]) >= 1


def test_chat_query() -> None:
    resp = client.post(
        "/api/v1/chat/query",
        json={
            "session_id": "test-session",
            "question": "What governance strengths does company 00001 disclose?",
            "stock_codes": ["00001"],
            "top_k": 5,
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert "answer" in payload
    assert isinstance(payload["citations"], list)
