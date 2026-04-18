from __future__ import annotations

from dataclasses import dataclass

from packages.ml.features import build_feature_vector
from packages.ml.keyword_extraction import extract_keywords
from packages.ml.labeling import label_sentences
from packages.ml.text_processing import sentence_split


@dataclass
class PipelineOutput:
    keywords: list[str]
    topic_counts: dict[str, int]
    density: float
    sentiment: dict[str, float]
    feature_vector: list[float]


def run_nlp_pipeline(document_text: str) -> PipelineOutput:
    sentences = sentence_split(document_text)
    labels = label_sentences(sentences)

    total_sent = max(labels["total_sentence_count"], 1)
    density = labels["esg_sentence_count"] / total_sent

    keywords = extract_keywords(sentences, top_n=12)
    vec = build_feature_vector(labels["topic_counts"], density, len(keywords))

    return PipelineOutput(
        keywords=keywords,
        topic_counts=labels["topic_counts"],
        density=density,
        sentiment=labels["sentiment"],
        feature_vector=vec.tolist(),
    )
