from __future__ import annotations

import math
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Chunk, Document
from app.services.openai_client import embed_text


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    length = min(len(a), len(b))
    dot = sum(a[i] * b[i] for i in range(length))
    norm_a = math.sqrt(sum(a[i] * a[i] for i in range(length)))
    norm_b = math.sqrt(sum(b[i] * b[i] for i in range(length)))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _lexical_score(query: str, text: str) -> float:
    q_tokens = set(re.findall(r"[a-zA-Z]{3,}", query.lower()))
    t_tokens = set(re.findall(r"[a-zA-Z]{3,}", text.lower()))
    if not q_tokens:
        return 0.0
    overlap = len(q_tokens.intersection(t_tokens))
    return overlap / len(q_tokens)


def retrieve_chunks(
    db: Session,
    question: str,
    stock_codes: list[str] | None = None,
    top_k: int = 8,
) -> list[dict[str, Any]]:
    stmt = (
        select(Chunk)
        .join(Document, Chunk.document_id == Document.id)
        .options(joinedload(Chunk.document).joinedload(Document.company))
    )
    if stock_codes:
        stmt = stmt.where(Document.stock_code.in_(stock_codes))

    chunks = list(db.scalars(stmt).all())
    if not chunks:
        return []

    query_emb = embed_text(question)
    scored: list[tuple[float, Chunk]] = []

    for chunk in chunks:
        emb = chunk.embedding
        semantic = 0.0
        if isinstance(emb, list) and emb:
            semantic = _cosine(query_emb, emb)
        lexical = _lexical_score(question, chunk.text)
        score = (semantic * 0.7) + (lexical * 0.3)
        scored.append((score, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)
    selected = scored[:top_k]

    payload: list[dict[str, Any]] = []
    for idx, (_, chunk) in enumerate(selected, start=1):
        doc = chunk.document
        payload.append(
            {
                "citation_id": f"C{idx}",
                "stock_code": doc.stock_code,
                "company_name": doc.company.company_name if doc.company else None,
                "doc_type": doc.doc_type,
                "source_file": doc.source_file,
                "page_no": chunk.page_no,
                "snippet": chunk.text[:360],
                "text": chunk.text,
            }
        )
    return payload


def build_context(citations: list[dict[str, Any]]) -> str:
    sections = []
    for c in citations:
        sections.append(
            f"[{c['citation_id']}] stock={c['stock_code']} doc={c['doc_type']} file={c['source_file']} page={c.get('page_no')}\n{c['text']}"
        )
    return "\n\n".join(sections)
