from __future__ import annotations

import hashlib
import math

from openai import OpenAI

from app.core.config import get_settings


def get_client() -> OpenAI | None:
    settings = get_settings()
    if not settings.openai_api_key:
        return None
    return OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)


def _hash_embedding(text: str, dims: int = 128) -> list[float]:
    # Deterministic fallback embedding for offline/dev mode.
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values = []
    for i in range(dims):
        b = digest[i % len(digest)]
        values.append((b / 255.0) * 2.0 - 1.0)
    norm = math.sqrt(sum(v * v for v in values)) or 1.0
    return [v / norm for v in values]


def embed_text(text: str) -> list[float]:
    settings = get_settings()
    client = get_client()
    if client is None:
        return _hash_embedding(text)

    response = client.embeddings.create(model=settings.embedding_model, input=[text])
    return response.data[0].embedding


def chat_completion(system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
    settings = get_settings()
    client = get_client()

    if client is None:
        return (
            "OpenAI key is not configured. Returning retrieval-grounded draft answer only.\n\n"
            + user_prompt[:1500]
        )

    response = client.chat.completions.create(
        model=settings.llm_model,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    content = response.choices[0].message.content
    return content or "No response generated."
