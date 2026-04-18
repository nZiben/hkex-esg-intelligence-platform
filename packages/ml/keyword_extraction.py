from __future__ import annotations

from app.services.nlp import extract_top_keywords


try:
    from keybert import KeyBERT
except Exception:  # pragma: no cover
    KeyBERT = None


def extract_keywords(texts: list[str], top_n: int = 12) -> list[str]:
    corpus = [t for t in texts if t.strip()]
    if not corpus:
        return []

    if KeyBERT is None:
        return extract_top_keywords(corpus, top_n=top_n)

    try:
        model = KeyBERT()
        joined = "\n".join(corpus)
        pairs = model.extract_keywords(joined, keyphrase_ngram_range=(1, 2), stop_words="english", top_n=top_n)
        return [term for term, _ in pairs]
    except Exception:
        return extract_top_keywords(corpus, top_n=top_n)
