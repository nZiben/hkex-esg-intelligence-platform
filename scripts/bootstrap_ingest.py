#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any

# Allow imports from monorepo packages.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))
sys.path.insert(0, str(ROOT))

from sqlalchemy import delete, select

from app.core.config import get_settings
from app.db import SessionLocal, init_db
from app.models import Chunk, Company, Document, ESGSignal, Prediction
from app.services.nlp import aggregate_sentiment, classify_topic, sentence_split
from app.services.openai_client import embed_text
from app.services.prediction import baseline_predict
from app.utils.rating import rating_to_ordinal
from packages.ml.text_processing import chunk_text, clean_pdf_text, infer_stock_code_from_filename

try:
    import fitz  # type: ignore
except Exception:  # pragma: no cover
    fitz = None

try:
    import pdfplumber  # type: ignore
except Exception:  # pragma: no cover
    pdfplumber = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap ingestion for ESG chatbot data.")
    parser.add_argument("--data-dir", default="data", help="Directory containing ZIP archives")
    parser.add_argument("--extract-dir", default="data/extracted", help="Extraction output directory")
    parser.add_argument("--processed-dir", default="data/processed", help="Processed output directory")
    parser.add_argument("--max-pdfs", type=int, default=None, help="Optional cap for PDF ingestion during quick tests")
    parser.add_argument("--skip-embeddings", action="store_true", help="Skip embedding generation")
    return parser.parse_args()


def extract_archives(data_dir: Path, extract_dir: Path) -> dict[str, Path]:
    extract_dir.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, Path] = {}

    for archive in sorted(data_dir.glob("*.zip")):
        stem = archive.name
        if stem.startswith("JSON"):
            target = extract_dir / "JSON"
        elif stem.startswith("PDFS_"):
            target = extract_dir / "PDFS_2"
        elif stem.startswith("PDFS"):
            target = extract_dir / "PDFS"
        else:
            continue

        if not target.exists() or not any(target.iterdir()):
            print(f"[ingest] extracting {archive.name} -> {target}")
            target.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(archive, "r") as zf:
                zf.extractall(extract_dir)

        outputs[target.name] = target

    return outputs


def read_pdf_text(pdf_path: Path) -> str:
    if fitz is not None:
        try:
            pages: list[str] = []
            doc = fitz.open(pdf_path)
            for page in doc:
                pages.append(page.get_text("text"))
            doc.close()
            text = "\n".join(pages)
            if text.strip():
                return remove_chinese_characters(text)
        except Exception:
            pass

    if pdfplumber is None:
        return ""

    try:
        pages: list[str] = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                pages.append(page.extract_text() or "")
        return remove_chinese_characters("\n".join(pages))
    except Exception:
        return ""


def remove_chinese_characters(text: str) -> str:
    return re.sub(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]+", "", text)


def upsert_company(db, payload: dict[str, Any]) -> Company:
    stock_code = str(payload.get("stock_code", "")).zfill(5)
    company = db.get(Company, stock_code)

    kwargs = {
        "stock_code": stock_code,
        "company_name": payload.get("company_name") or stock_code,
        "industry": payload.get("industry"),
        "esg_rating_raw": payload.get("esg_rating"),
        "esg_rating_ordinal": rating_to_ordinal(payload.get("esg_rating")),
        "universe_ranking": payload.get("universe_ranking"),
        "peer_ranking": payload.get("peer_ranking"),
        "strengths": payload.get("strengths") or [],
        "weaknesses": payload.get("weaknesses") or [],
        "index_membership": payload.get("index_membership") or [],
    }

    if company is None:
        company = Company(**kwargs)
        db.add(company)
    else:
        for key, value in kwargs.items():
            setattr(company, key, value)

    return company


def upsert_document(db, stock_code: str, doc_type: str, source_file: str, text_clean: str) -> Document:
    existing = db.scalars(
        select(Document).where(
            Document.stock_code == stock_code,
            Document.doc_type == doc_type,
            Document.source_file == source_file,
        )
    ).first()

    if existing is None:
        existing = Document(
            stock_code=stock_code,
            doc_type=doc_type,
            source_file=source_file,
            text_clean=text_clean,
        )
        db.add(existing)
        db.flush()
    else:
        existing.text_clean = text_clean

    db.execute(delete(Chunk).where(Chunk.document_id == existing.id))
    db.flush()
    return existing


def compute_signal_from_text(text: str) -> dict[str, Any]:
    sents = sentence_split(text)
    topic_counts = {"E": 0, "S": 0, "G": 0, "Mixed": 0}
    esg_sents: list[str] = []

    for s in sents:
        label = classify_topic(s)
        topic_counts[label] = topic_counts.get(label, 0) + 1
        if label in {"E", "S", "G", "Mixed"}:
            esg_sents.append(s)

    pos, neu, neg = aggregate_sentiment(esg_sents)
    density = len(esg_sents) / max(len(sents), 1)

    return {
        "topic_counts": topic_counts,
        "density": density,
        "sentiment": {"pos": pos, "neu": neu, "neg": neg},
    }


def main() -> None:
    args = parse_args()
    settings = get_settings()

    data_dir = Path(args.data_dir)
    extract_dir = Path(args.extract_dir)
    processed_dir = Path(args.processed_dir)
    processed_dir.mkdir(parents=True, exist_ok=True)

    extracted = extract_archives(data_dir=data_dir, extract_dir=extract_dir)
    json_dir = extracted.get("JSON", extract_dir / "JSON")
    esg_pdf_dir = extracted.get("PDFS", extract_dir / "PDFS")
    annual_pdf_dir = extracted.get("PDFS_2", extract_dir / "PDFS_2")

    init_db()

    summary_rows = []
    agg_by_company: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "E": 0,
            "S": 0,
            "G": 0,
            "Mixed": 0,
            "density_sum": 0.0,
            "doc_count": 0,
            "pos_sum": 0.0,
            "neu_sum": 0.0,
            "neg_sum": 0.0,
        }
    )

    with SessionLocal() as db:
        json_files = sorted(json_dir.glob("*.json")) if json_dir.exists() else []
        print(f"[ingest] loading company metadata JSON files: {len(json_files)}")
        for jf in json_files:
            payload = json.loads(jf.read_text(encoding="utf-8"))
            upsert_company(db, payload)
        db.commit()

        pdf_targets: list[tuple[Path, str]] = []
        if esg_pdf_dir.exists():
            pdf_targets.extend((p, "esg_report") for p in sorted(esg_pdf_dir.glob("*.pdf")))
        if annual_pdf_dir.exists():
            pdf_targets.extend((p, "annual_report") for p in sorted(annual_pdf_dir.glob("*.pdf")))

        if args.max_pdfs:
            pdf_targets = pdf_targets[: args.max_pdfs]

        print(f"[ingest] processing PDF documents: {len(pdf_targets)}")

        for idx, (pdf_path, doc_type) in enumerate(pdf_targets, start=1):
            stock_code = infer_stock_code_from_filename(pdf_path)
            company = db.get(Company, stock_code)
            if company is None:
                company = Company(
                    stock_code=stock_code,
                    company_name=f"Company {stock_code}",
                    industry="Unknown",
                )
                db.add(company)
                db.flush()

            raw_text = read_pdf_text(pdf_path)
            cleaned = clean_pdf_text(raw_text)
            if not cleaned:
                continue

            doc = upsert_document(
                db,
                stock_code=stock_code,
                doc_type=doc_type,
                source_file=pdf_path.name,
                text_clean=cleaned,
            )

            chunks = chunk_text(cleaned, chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap)
            for cidx, chunk in enumerate(chunks):
                emb = None
                if not args.skip_embeddings:
                    try:
                        emb = embed_text(chunk)
                    except Exception:
                        emb = None
                db.add(
                    Chunk(
                        document_id=doc.id,
                        chunk_index=cidx,
                        text=chunk,
                        embedding=emb,
                        page_no=None,
                    )
                )

            signal = compute_signal_from_text(cleaned)
            company_agg = agg_by_company[stock_code]
            company_agg["E"] += signal["topic_counts"].get("E", 0)
            company_agg["S"] += signal["topic_counts"].get("S", 0)
            company_agg["G"] += signal["topic_counts"].get("G", 0)
            company_agg["Mixed"] += signal["topic_counts"].get("Mixed", 0)
            company_agg["density_sum"] += signal["density"]
            company_agg["doc_count"] += 1
            company_agg["pos_sum"] += signal["sentiment"]["pos"]
            company_agg["neu_sum"] += signal["sentiment"]["neu"]
            company_agg["neg_sum"] += signal["sentiment"]["neg"]

            summary_rows.append(
                {
                    "stock_code": stock_code,
                    "source_file": pdf_path.name,
                    "doc_type": doc_type,
                    "chunks": len(chunks),
                    "e_count": signal["topic_counts"].get("E", 0),
                    "s_count": signal["topic_counts"].get("S", 0),
                    "g_count": signal["topic_counts"].get("G", 0),
                    "mixed_count": signal["topic_counts"].get("Mixed", 0),
                    "esg_density": round(signal["density"], 4),
                }
            )

            if idx % 10 == 0:
                db.commit()
                print(f"[ingest] processed {idx}/{len(pdf_targets)} PDFs")

        db.commit()

        for stock_code, agg in agg_by_company.items():
            doc_count = max(agg["doc_count"], 1)
            density = agg["density_sum"] / doc_count
            pos = agg["pos_sum"] / doc_count
            neu = agg["neu_sum"] / doc_count
            neg = agg["neg_sum"] / doc_count

            existing = db.get(ESGSignal, stock_code)
            if existing is None:
                existing = ESGSignal(stock_code=stock_code)
                db.add(existing)

            existing.e_count = int(agg["E"])
            existing.s_count = int(agg["S"])
            existing.g_count = int(agg["G"])
            existing.mixed_count = int(agg["Mixed"])
            existing.esg_density = float(round(density, 4))
            existing.sentiment_pos = float(round(pos, 4))
            existing.sentiment_neu = float(round(neu, 4))
            existing.sentiment_neg = float(round(neg, 4))

            pred = baseline_predict(existing.e_count, existing.s_count, existing.g_count, existing.esg_density)
            db.add(
                Prediction(
                    stock_code=stock_code,
                    predicted_esg_rating=pred.rating,
                    confidence=pred.confidence,
                    model_version="baseline-v1",
                )
            )

        db.commit()

    # Write summary CSV without pandas dependency here.
    csv_path = processed_dir / "company_summary.csv"
    headers = [
        "stock_code",
        "source_file",
        "doc_type",
        "chunks",
        "e_count",
        "s_count",
        "g_count",
        "mixed_count",
        "esg_density",
    ]
    with csv_path.open("w", encoding="utf-8") as f:
        f.write(",".join(headers) + "\n")
        for row in summary_rows:
            f.write(",".join(str(row[h]) for h in headers) + "\n")

    print("[ingest] done")
    print(f"[ingest] wrote {csv_path}")


if __name__ == "__main__":
    main()
