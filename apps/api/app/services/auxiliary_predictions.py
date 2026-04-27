from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import torch
import torch.nn.functional as F

from app.core.config import get_settings
from app.services.model_prediction import PredictionInputError, PredictionModelUnavailable, _collect_prediction_chunks

TOPICS = [
    "Community Involvement and Development",
    "Consumer Issues",
    "Corporate Governance",
    "Environment",
    "Fair Operating Practices",
    "Human Rights",
    "Labour Practices",
]

THEME_ANCHORS = {
    "Carbon Footprint": "Upstream/downstream emissions, carbon offsets, methane leakage, GWP (Global Warming Potential).",
    "Energy Management": "Energy intensity, grid decarbonization, thermal efficiency, microgrid integration.",
    "Water Stewardship": "Total water consumption, water stress indexing, desalination, effluent quality.",
    "Waste Mitigation": "Hazardous waste incineration, e-waste recovery, plastic neutrality, single-use reduction.",
    "Climate Strategy": "TCFD alignment, SBTi (Science Based Targets), internal carbon pricing, stranded assets.",
    "Biodiversity": "TNFD framework, deforestation-free supply chains, land degradation neutrality.",
    "Pollution Control": "Sulfur Oxides (SOx), VOCs (Volatile Organic Compounds), heavy metal discharge.",
    "Green Finance": "EU Taxonomy alignment, transition bonds, sustainability-linked loans.",
    "Resource Efficiency": "Life cycle assessment (LCA), dematerialization, regenerative agriculture.",
    "Environmental Compliance": "Environmental permits, HKEX Appendix 27 mandatory disclosure, remediation costs.",
    "Labor Practices": "Freedom of association, gig economy protections, living wage vs. minimum wage.",
    "Health & Safety": "TRIR (Total Recordable Incident Rate), near-miss reporting, industrial hygiene.",
    "Human Rights": "Modern slavery statement, conflict minerals, indigenous rights, migrant labor.",
    "Diversity & Inclusion": "Board gender diversity, pay equity audits, accessibility standards, inclusive hiring.",
    "Talent Development": "Attrition rate, upskilling programs, leadership succession, tuition reimbursement.",
    "Community Impact": "Social License to Operate (SLO), local procurement, disaster relief.",
    "Product Safety": "Product liability, chemical safety (REACH/RoHS), quality management systems.",
    "Privacy & Data": "GDPR compliance, data breach frequency, encryption standards, user consent.",
    "Employee Well-being": "Burnout prevention, flexible work arrangements, employee assistance programs (EAP).",
    "Stakeholder Engagement": "Investor relations, NGO partnerships, customer churn, grievance mechanisms.",
    "Board Composition": "CEO/Chair separation, refreshment policies, interlocking directorates, independence ratio.",
    "Executive Pay": "Clawback provisions, ESG-linked vesting, Say-on-Pay results, equity ownership.",
    "Audit & Oversight": "Internal control weakness, auditor rotation, forensic accounting, SOX compliance.",
    "Business Ethics": "Anti-Money Laundering (AML), KYC (Know Your Customer), lobbying transparency.",
    "Risk Management": "Climate scenario analysis, supply chain resilience, geopolitical risk, credit risk.",
    "Shareholder Rights": "Proxy access, dual-class structures, supermajority voting, poison pill provisions.",
    "Transparency": "Integrated reporting, GRI standards, SASB alignment, double materiality.",
    "Regulatory Compliance": "Anti-bribery/corruption (ABC), listing rule adherence, sanctions screening.",
    "Sustainability Oversight": "ESG committee charter, materiality assessment, C-suite sustainability roles.",
    "Political Engagement": "PAC contributions, trade association alignment, policy advocacy, public funding.",
}

SENTIMENT_ANCHORS = {
    "E": {
        "pos": [
            "Achieved absolute reduction in greenhouse gas emissions across all scopes.",
            "Successfully transitioned operations to 100% renewable energy procurement.",
            "Implemented zero-waste-to-landfill protocols throughout the supply chain.",
            "Surpassed water conservation targets through advanced recycling technology.",
            "Adopted comprehensive circular economy principles in product design.",
            "Demonstrated leadership in low-carbon innovation and green technology.",
            "Successfully mitigated climate-related financial risks through strategic planning.",
            "Ensured full compliance with international environmental protection standards.",
            "Eliminated the use of hazardous chemicals in manufacturing processes.",
            "Invested significantly in local biodiversity restoration and protection.",
        ],
        "neg": [
            "Significant increase in carbon intensity and total energy consumption.",
            "Persistent failure to meet established emission reduction targets.",
            "Involved in severe environmental pollution incidents and chemical leaks.",
            "Continued heavy reliance on fossil fuels without transition planning.",
            "Ineffective waste management resulting in high plastic waste output.",
            "Excessive depletion of local water resources in water-stressed regions.",
            "Irreversible destruction of natural habitats and local ecosystems.",
            "Repeated non-compliance with environmental regulations and laws.",
            "Lack of investment in climate adaptation or mitigation strategies.",
            "Opaque reporting on environmental impact and resource usage.",
        ],
    },
    "S": {
        "pos": [
            "Maintained superior occupational health and safety metrics with zero fatalities.",
            "Achieved high workforce diversity and inclusion at the leadership level.",
            "Strict enforcement of fair labor practices and human rights standards.",
            "Implemented extensive employee professional development and training programs.",
            "Demonstrated strong community engagement and social investment impact.",
            "Maintained high employee retention rates and positive workplace morale.",
            "Conducted rigorous human rights due diligence across global operations.",
            "Ensured equal pay for equal work and gender pay equity.",
            "Supported workforce well-being through comprehensive mental health initiatives.",
            "Applied stringent safety and ethical standards to all third-party vendors.",
        ],
        "neg": [
            "Severe workplace safety violations resulting in preventable injuries.",
            "Documented cases of discriminatory hiring and promotion practices.",
            "Evidence of forced labor or child labor within the supply chain.",
            "Ongoing conflicts with local communities regarding land or use.",
            "Significant lack of gender and ethnic diversity in executive positions.",
            "Stagnant wages and reduction of essential employee benefits.",
            "Neglect of human rights protocols in high-risk operational regions.",
            "Inadequate investment in workforce safety equipment and training.",
            "Extreme staff turnover rates driven by poor management culture.",
            "Systemic disregard for employee work-life balance and mental health.",
        ],
    },
    "G": {
        "pos": [
            "Established a highly independent board with diverse expertise.",
            "Maintained full transparency in financial and ESG disclosure reporting.",
            "Implemented a robust and effective enterprise risk management framework.",
            "Strict adherence to anti-corruption, bribery, and ethics policies.",
            "Conducted regular and thorough independent internal audit procedures.",
            "Aligned executive compensation directly with long-term ESG performance.",
            "Proactive and consistent compliance with all HKEX listing requirements.",
            "Maintained open and transparent communication channels with all stakeholders.",
            "Ensured top-tier data privacy protection and cybersecurity resilience.",
            "Clearly defined accountability structures for ESG strategy oversight.",
        ],
        "neg": [
            "Involved in corporate fraud and systemic ethical misconduct.",
            "Critical lack of independent oversight on the board of directors.",
            "Unresolved conflicts of interest among key executive decision-makers.",
            "Major data security breaches resulting in loss of stakeholder trust.",
            "Deliberate non-compliance with regulatory and financial reporting rules.",
            "Opaque and excessive executive compensation unrelated to performance.",
            "Failure to identify or mitigate material business risks effectively.",
            "Ineffective audit committee and weak internal financial controls.",
            "Serious allegations of bribery and corrupt business dealings.",
            "Weak stakeholder engagement resulting in poor corporate accountability.",
        ],
    },
}

THEME_SIMILARITY_THRESHOLD = 0.65
SENTIMENT_BIAS_THRESHOLD = 0.03


class MultiLabelClassifier(torch.nn.Module):
    def __init__(self, input_dim: int, num_labels: int):
        super().__init__()
        self.net = torch.nn.Sequential(
            torch.nn.Linear(input_dim, 512),
            torch.nn.ReLU(),
            torch.nn.Dropout(0.2),
            torch.nn.Linear(512, 128),
            torch.nn.ReLU(),
            torch.nn.Linear(128, num_labels),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


@dataclass(frozen=True)
class AuxiliaryModelBundle:
    retriever: object
    topic_classifier: MultiLabelClassifier
    theme_names: list[str]
    theme_embeddings: torch.Tensor
    sentiment_embeddings: dict[str, dict[str, torch.Tensor]]
    device: str


@dataclass(frozen=True)
class TopicPrediction:
    label: str
    probability: float
    predicted: bool


@dataclass(frozen=True)
class ThemePrediction:
    theme: str
    mentions: int
    share: float


@dataclass(frozen=True)
class SentimentPrediction:
    pillar: str
    sentiment: str
    positive_similarity: float
    negative_similarity: float
    margin: float


@dataclass(frozen=True)
class AuxiliaryPrediction:
    stock_code: str
    company_name: str
    prediction_type: str
    model_version: str
    num_chunks: int
    doc_count: int
    topics: list[TopicPrediction]
    themes: list[ThemePrediction]
    sentiment: list[SentimentPrediction]


def _artifact_paths() -> tuple[Path, Path]:
    model_root = Path(get_settings().prediction_model_root)
    return model_root / "retriever", model_root / "topic_classifier" / "classifier.pt"


@lru_cache(maxsize=1)
def load_auxiliary_model_bundle() -> AuxiliaryModelBundle:
    retriever_path, topic_classifier_path = _artifact_paths()
    missing = [str(path) for path in [retriever_path, topic_classifier_path] if not path.exists()]
    if missing:
        raise PredictionModelUnavailable(f"Auxiliary prediction artifacts are missing: {', '.join(missing)}")

    try:
        from sentence_transformers import SentenceTransformer
    except Exception as exc:  # pragma: no cover - dependency failure path
        raise PredictionModelUnavailable("sentence-transformers is required for ESG auxiliary predictions") from exc

    device = "cuda" if torch.cuda.is_available() else "cpu"
    retriever = SentenceTransformer(str(retriever_path), device=device)
    sample_emb = retriever.encode(["test"], convert_to_numpy=True, show_progress_bar=False)
    input_dim = int(sample_emb.shape[1])

    topic_classifier = MultiLabelClassifier(input_dim=input_dim, num_labels=len(TOPICS)).to(device)
    topic_classifier.load_state_dict(torch.load(topic_classifier_path, map_location=device))
    topic_classifier.eval()

    theme_names = list(THEME_ANCHORS.keys())
    theme_descriptions = list(THEME_ANCHORS.values())
    with torch.no_grad():
        theme_embeddings = retriever.encode(theme_descriptions, convert_to_tensor=True).to(device)
        sentiment_embeddings = {
            pillar: {
                "pos": retriever.encode(anchor_set["pos"], convert_to_tensor=True).to(device).mean(0),
                "neg": retriever.encode(anchor_set["neg"], convert_to_tensor=True).to(device).mean(0),
            }
            for pillar, anchor_set in SENTIMENT_ANCHORS.items()
        }

    return AuxiliaryModelBundle(
        retriever=retriever,
        topic_classifier=topic_classifier,
        theme_names=theme_names,
        theme_embeddings=theme_embeddings,
        sentiment_embeddings=sentiment_embeddings,
        device=device,
    )


def run_auxiliary_prediction(db, stock_code: str, prediction_type: str = "all") -> AuxiliaryPrediction:
    settings = get_settings()
    company, chunks, doc_count = _collect_prediction_chunks(db, stock_code)
    bundle = load_auxiliary_model_bundle()

    chunks_to_encode = chunks[: settings.prediction_max_chunks]
    with torch.no_grad():
        embeddings = bundle.retriever.encode(
            chunks_to_encode,
            batch_size=settings.prediction_batch_size,
            convert_to_tensor=True,
            show_progress_bar=False,
        ).to(bundle.device)

    if embeddings.ndim != 2 or embeddings.shape[0] == 0:
        raise PredictionInputError("Auxiliary model did not produce valid embeddings")

    doc_embedding = embeddings.mean(0)
    include_topics = prediction_type in {"topics", "all"}
    include_themes = prediction_type in {"themes", "all"}
    include_sentiment = prediction_type in {"sentiment", "all"}

    return AuxiliaryPrediction(
        stock_code=company.stock_code,
        company_name=company.company_name,
        prediction_type=prediction_type,
        model_version="topic-theme-sentiment-v1",
        num_chunks=len(chunks),
        doc_count=doc_count,
        topics=_predict_topics(bundle, doc_embedding) if include_topics else [],
        themes=_predict_themes(bundle, embeddings) if include_themes else [],
        sentiment=_predict_sentiment(bundle, doc_embedding) if include_sentiment else [],
    )


def _predict_topics(bundle: AuxiliaryModelBundle, doc_embedding: torch.Tensor) -> list[TopicPrediction]:
    with torch.no_grad():
        logits = bundle.topic_classifier(doc_embedding.unsqueeze(0))
        probs = torch.sigmoid(logits).detach().cpu().numpy()[0]

    predictions = [
        TopicPrediction(label=topic, probability=round(float(prob), 4), predicted=bool(prob >= 0.5))
        for topic, prob in zip(TOPICS, probs, strict=True)
    ]
    return sorted(predictions, key=lambda item: item.probability, reverse=True)


def _predict_themes(bundle: AuxiliaryModelBundle, chunk_embeddings: torch.Tensor) -> list[ThemePrediction]:
    with torch.no_grad():
        similarities = F.cosine_similarity(
            chunk_embeddings.unsqueeze(1),
            bundle.theme_embeddings.unsqueeze(0),
            dim=2,
        )
        counts = (similarities > THEME_SIMILARITY_THRESHOLD).sum(dim=0).detach().cpu().numpy()

    theme_rows = [
        ThemePrediction(
            theme=theme,
            mentions=int(count),
            share=round(float(count / max(1, chunk_embeddings.shape[0])), 4),
        )
        for theme, count in zip(bundle.theme_names, counts, strict=True)
        if int(count) > 0
    ]
    return sorted(theme_rows, key=lambda item: item.mentions, reverse=True)[:15]


def _predict_sentiment(bundle: AuxiliaryModelBundle, doc_embedding: torch.Tensor) -> list[SentimentPrediction]:
    rows = []
    with torch.no_grad():
        for pillar in ["E", "S", "G"]:
            anchors = bundle.sentiment_embeddings[pillar]
            pos_sim = F.cosine_similarity(doc_embedding.unsqueeze(0), anchors["pos"].unsqueeze(0)).item()
            neg_sim = F.cosine_similarity(doc_embedding.unsqueeze(0), anchors["neg"].unsqueeze(0)).item()
            margin = pos_sim - neg_sim
            if margin > SENTIMENT_BIAS_THRESHOLD:
                sentiment = "positive"
            elif margin < -SENTIMENT_BIAS_THRESHOLD:
                sentiment = "negative"
            else:
                sentiment = "neutral"

            rows.append(
                SentimentPrediction(
                    pillar=pillar,
                    sentiment=sentiment,
                    positive_similarity=round(float(pos_sim), 4),
                    negative_similarity=round(float(neg_sim), 4),
                    margin=round(float(margin), 4),
                )
            )

    return rows
