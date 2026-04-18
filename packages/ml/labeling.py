from __future__ import annotations

from collections import Counter

from app.services.nlp import aggregate_sentiment, classify_topic


def label_sentences(sentences: list[str]) -> dict:
    topic_counts = Counter()
    esg_sentences: list[str] = []

    for sent in sentences:
        topic = classify_topic(sent)
        topic_counts[topic] += 1
        if topic in {"E", "S", "G", "Mixed"}:
            esg_sentences.append(sent)

    pos, neu, neg = aggregate_sentiment(esg_sentences)

    return {
        "topic_counts": dict(topic_counts),
        "esg_sentence_count": len(esg_sentences),
        "total_sentence_count": len(sentences),
        "sentiment": {
            "positive": pos,
            "neutral": neu,
            "negative": neg,
        },
    }
