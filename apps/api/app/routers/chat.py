from __future__ import annotations

import time

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db import get_db
from app.models import ChatLog
from app.schemas import ChatQueryRequest, ChatQueryResponse, Citation
from app.services.nlp import confidence_from_support
from app.services.openai_client import chat_completion
from app.services.retrieval import build_context, retrieve_chunks

router = APIRouter(prefix="/api/v1", tags=["chat"])


@router.post("/chat/query", response_model=ChatQueryResponse)
def query_chat(payload: ChatQueryRequest, db: Session = Depends(get_db)) -> ChatQueryResponse:
    settings = get_settings()
    start = time.perf_counter()

    citations_raw = retrieve_chunks(
        db=db,
        question=payload.question,
        stock_codes=payload.stock_codes,
        top_k=min(payload.top_k, settings.max_context_chunks),
    )

    context = build_context(citations_raw)
    system_prompt = (
        "You are an ESG analyst assistant. Use only provided citations. "
        "If evidence is missing, state limitations explicitly. "
        "Always cite in [C#] format."
    )
    user_prompt = (
        f"Question: {payload.question}\n\n"
        f"Evidence Context:\n{context}\n\n"
        "Respond with concise business insight, cite supporting evidence, "
        "and include 2 follow-up questions."
    )

    answer = chat_completion(system_prompt=system_prompt, user_prompt=user_prompt)

    latency_ms = int((time.perf_counter() - start) * 1000)
    confidence = round(confidence_from_support(len(citations_raw)), 3)

    follow_ups = [
        "Would you like a side-by-side ESG comparison with another company?",
        "Do you want a trend-focused summary for Environmental versus Governance disclosures?",
    ]

    db.add(
        ChatLog(
            session_id=payload.session_id,
            question=payload.question,
            answer=answer,
            citations_json=citations_raw,
            confidence=confidence,
            latency_ms=latency_ms,
        )
    )
    db.commit()

    citations = [Citation(**{k: c[k] for k in Citation.model_fields}) for c in citations_raw]
    return ChatQueryResponse(
        answer=answer,
        citations=citations,
        confidence=confidence,
        latency_ms=latency_ms,
        follow_up_questions=follow_ups,
    )
