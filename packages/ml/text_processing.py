from __future__ import annotations

import re
from pathlib import Path


def clean_pdf_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"Page\s+\d+\s+of\s+\d+", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(HKEX|ANNUAL REPORT|ESG REPORT)\b", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def sentence_split(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if len(p.strip()) > 25]


def chunk_text(text: str, chunk_size: int = 900, chunk_overlap: int = 120) -> list[str]:
    cleaned = clean_pdf_text(text)
    if len(cleaned) <= chunk_size:
        return [cleaned] if cleaned else []

    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(start + chunk_size, len(cleaned))
        chunk = cleaned[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(cleaned):
            break
        start = max(0, end - chunk_overlap)
    return chunks


def infer_stock_code_from_filename(path: str | Path) -> str:
    name = Path(path).stem
    digits = "".join(ch for ch in name if ch.isdigit())
    return digits.zfill(5)[-5:]
