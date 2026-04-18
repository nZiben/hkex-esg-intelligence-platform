#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))
sys.path.insert(0, str(ROOT))

from app.db import SessionLocal, init_db
from app.models import Company, ESGSignal


def main() -> None:
    init_db()
    output_dir = ROOT / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)

    with SessionLocal() as db:
        companies = db.scalars(select(Company)).all()
        signals = db.scalars(select(ESGSignal)).all()

    company_df = pd.DataFrame(
        [
            {
                "stock_code": c.stock_code,
                "company_name": c.company_name,
                "industry": c.industry,
                "esg_rating_raw": c.esg_rating_raw,
                "esg_rating_ordinal": c.esg_rating_ordinal,
            }
            for c in companies
        ]
    )

    signal_df = pd.DataFrame(
        [
            {
                "stock_code": s.stock_code,
                "e_count": s.e_count,
                "s_count": s.s_count,
                "g_count": s.g_count,
                "mixed_count": s.mixed_count,
                "esg_density": s.esg_density,
                "sentiment_pos": s.sentiment_pos,
                "sentiment_neu": s.sentiment_neu,
                "sentiment_neg": s.sentiment_neg,
            }
            for s in signals
        ]
    )

    merged = company_df.merge(signal_df, on="stock_code", how="left") if not company_df.empty else signal_df

    csv_path = output_dir / "chapter4_company_signals.csv"
    merged.to_csv(csv_path, index=False)

    if not signal_df.empty:
        plt.figure(figsize=(9, 5))
        topic_totals = signal_df[["e_count", "s_count", "g_count", "mixed_count"]].sum()
        topic_totals.index = ["Environmental", "Social", "Governance", "Mixed"]
        topic_totals.plot(kind="bar", color=["#3e8f6d", "#d08b3e", "#325f8a", "#8f8f8f"])
        plt.title("Aggregate ESG Topic Distribution")
        plt.ylabel("Sentence Count")
        plt.tight_layout()
        plt.savefig(output_dir / "chapter4_topic_distribution.png", dpi=180)
        plt.close()

        plt.figure(figsize=(9, 5))
        signal_df["esg_density"].plot(kind="hist", bins=20, color="#2f6c8f")
        plt.title("ESG Disclosure Density Distribution")
        plt.xlabel("ESG Density")
        plt.tight_layout()
        plt.savefig(output_dir / "chapter4_esg_density_hist.png", dpi=180)
        plt.close()

    print(f"[report] wrote {csv_path}")


if __name__ == "__main__":
    main()
