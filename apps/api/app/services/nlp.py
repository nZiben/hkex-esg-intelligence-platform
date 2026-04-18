from __future__ import annotations

import math
import re
from collections import Counter

from sklearn.feature_extraction.text import TfidfVectorizer

TOPIC_KEYWORDS = {
    "E": {
        "emission",
        "carbon",
        "energy",
        "water",
        "waste",
        "green",
        "climate",
        "pollution",
        "renewable",
    },
    "S": {
        "employee",
        "health",
        "safety",
        "community",
        "training",
        "diversity",
        "human",
        "labor",
        "inclusion",
    },
    "G": {
        "board",
        "audit",
        "risk",
        "compliance",
        "governance",
        "committee",
        "ethics",
        "regulation",
        "policy",
    },
}

POSITIVE_WORDS = {
    "improve",
    "improved",
    "increase",
    "increased",
    "strong",
    "positive",
    "reduced",
    "success",
    "efficient",
    "effective",
}
NEGATIVE_WORDS = {
    "decline",
    "decreased",
    "penalty",
    "risk",
    "incident",
    "fine",
    "negative",
    "weak",
    "failure",
    "breach",
}


def sentence_split(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if len(p.strip()) > 25]


def classify_topic(sentence: str) -> str:
    lowered = sentence.lower()
    hits = {label: 0 for label in TOPIC_KEYWORDS}
    for label, words in TOPIC_KEYWORDS.items():
        hits[label] = sum(1 for w in words if w in lowered)

    ranked = sorted(hits.items(), key=lambda x: x[1], reverse=True)
    if ranked[0][1] == 0:
        return "Mixed"
    if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
        return "Mixed"
    return ranked[0][0]


def sentiment_score(sentence: str) -> float:
    tokens = re.findall(r"[a-zA-Z]+", sentence.lower())
    if not tokens:
        return 0.0
    pos = sum(1 for t in tokens if t in POSITIVE_WORDS)
    neg = sum(1 for t in tokens if t in NEGATIVE_WORDS)
    return (pos - neg) / max(len(tokens), 1)


def aggregate_sentiment(sentences: list[str]) -> tuple[float, float, float]:
    if not sentences:
        return (0.0, 1.0, 0.0)

    pos = neu = neg = 0
    for s in sentences:
        score = sentiment_score(s)
        if score > 0.015:
            pos += 1
        elif score < -0.015:
            neg += 1
        else:
            neu += 1

    total = max(len(sentences), 1)
    return (pos / total, neu / total, neg / total)


def extract_top_keywords(texts: list[str], top_n: int = 12) -> list[str]:
    corpus = [t for t in texts if t.strip()]
    if not corpus:
        return []

    try:
        vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=4000)
        matrix = vectorizer.fit_transform(corpus)
        mean_scores = matrix.mean(axis=0).A1
        terms = vectorizer.get_feature_names_out()
        top_idx = mean_scores.argsort()[::-1][:top_n]
        return [terms[i] for i in top_idx]
    except Exception:
        bag = Counter(re.findall(r"[a-zA-Z]{4,}", " ".join(corpus).lower()))
        return [word for word, _ in bag.most_common(top_n)]


def count_topics(sentences: list[str]) -> dict[str, int]:
    counts = {"E": 0, "S": 0, "G": 0, "Mixed": 0}
    for sent in sentences:
        topic = classify_topic(sent)
        counts[topic] = counts.get(topic, 0) + 1
    return counts


def esg_density(esg_sentence_count: int, total_sentence_count: int) -> float:
    if total_sentence_count <= 0:
        return 0.0
    return round(esg_sentence_count / total_sentence_count, 4)


def confidence_from_support(citations: int) -> float:
    return max(0.45, min(0.95, 0.55 + math.log1p(citations) / 4))
