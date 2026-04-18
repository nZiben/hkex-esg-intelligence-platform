#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))
sys.path.insert(0, str(ROOT))

from packages.ml.retriever_finetune import (
    build_triplets_from_db_rows,
    build_triplets_from_json_zip,
    save_triplets_jsonl,
    train_retriever_triplet_model,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run real retriever fine-tuning on ESG data.")
    parser.add_argument("--data-dir", default="data", help="Directory containing data archives")
    parser.add_argument("--json-zip", default="", help="Optional explicit JSON zip path")
    parser.add_argument("--output-dir", default="artifacts/finetuned-retriever", help="Output checkpoint directory")
    parser.add_argument(
        "--triplets-out",
        default="artifacts/finetuned-retriever/retriever_triplets.jsonl",
        help="Triplet dataset output path",
    )
    parser.add_argument("--model", default="sentence-transformers/all-MiniLM-L6-v2", help="Base embedding model")
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=24)
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--max-triplets", type=int, default=3000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--source", choices=["auto", "db", "json"], default="auto")
    parser.add_argument("--prepare-only", action="store_true", help="Build and save triplets only; skip training")
    return parser.parse_args()


def _resolve_json_zip(data_dir: Path, explicit: str) -> Path:
    if explicit:
        path = Path(explicit)
        if not path.exists():
            raise FileNotFoundError(f"--json-zip not found: {path}")
        return path

    candidates = sorted(data_dir.glob("JSON*.zip"))
    if not candidates:
        raise FileNotFoundError("No JSON*.zip archive found in data directory.")
    return candidates[0]


def _fetch_db_rows(limit: int = 15000) -> list[dict]:
    from sqlalchemy import select

    from app.db import SessionLocal, init_db
    from app.models import Chunk, Company, Document

    init_db()
    with SessionLocal() as db:
        stmt = (
            select(Chunk.text, Document.stock_code, Document.doc_type, Company.company_name)
            .join(Document, Chunk.document_id == Document.id)
            .join(Company, Document.stock_code == Company.stock_code)
            .limit(limit)
        )
        rows = db.execute(stmt).all()

    payload = [
        {
            "text": row[0],
            "stock_code": row[1],
            "doc_type": row[2],
            "company_name": row[3],
        }
        for row in rows
        if row[0]
    ]
    return payload


def main() -> None:
    args = parse_args()
    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    triplets_out = Path(args.triplets_out)

    source = args.source
    triplets = []

    if source in {"auto", "db"}:
        try:
            db_rows = _fetch_db_rows()
            if db_rows:
                triplets = build_triplets_from_db_rows(db_rows, max_triplets=args.max_triplets, seed=args.seed)
                source = "db"
        except Exception as exc:
            if args.source == "db":
                raise
            print(f"[finetune] DB source unavailable, falling back to JSON. reason={exc}")

    if not triplets:
        json_zip = _resolve_json_zip(data_dir, args.json_zip)
        triplets = build_triplets_from_json_zip(json_zip, max_triplets=args.max_triplets, seed=args.seed)
        source = "json"

    if len(triplets) < 30:
        raise RuntimeError(f"Only {len(triplets)} triplets generated. Need at least 30.")

    save_triplets_jsonl(triplets, triplets_out)
    print(f"[finetune] source={source} triplets={len(triplets)} saved={triplets_out}")

    if args.prepare_only:
        return

    report = train_retriever_triplet_model(
        triplets=triplets,
        model_name=args.model,
        output_dir=output_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        seed=args.seed,
    )

    report_path = output_dir / "finetune_report.json"
    report_path.write_text(json.dumps(report.__dict__, indent=2), encoding="utf-8")

    print("[finetune] completed")
    print(json.dumps(report.__dict__, indent=2))
    print(f"[finetune] report={report_path}")


if __name__ == "__main__":
    main()
