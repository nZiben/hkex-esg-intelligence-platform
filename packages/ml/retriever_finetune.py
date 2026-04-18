from __future__ import annotations

import json
import random
import re
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

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


@dataclass
class TripletRecord:
    query: str
    positive: str
    negative: str
    topic: str
    stock_code: str
    source: str


@dataclass
class FinetuneReport:
    source: str
    training_backend: str
    model_name: str
    output_dir: str
    triplet_count: int
    train_triplets: int
    val_triplets: int
    epochs: int
    batch_size: int
    lr: float
    baseline_triplet_accuracy: float
    tuned_triplet_accuracy: float


def classify_topic(text: str) -> str:
    lowered = text.lower()
    counts = {k: 0 for k in TOPIC_KEYWORDS}
    for label, words in TOPIC_KEYWORDS.items():
        counts[label] = sum(1 for w in words if w in lowered)

    ranked = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    if ranked[0][1] == 0:
        return "Mixed"
    if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
        return "Mixed"
    return ranked[0][0]


def _topic_query(topic: str, stock_code: str, company_name: str | None = None) -> str:
    comp = company_name or f"company {stock_code}"
    if topic == "E":
        return f"What environmental disclosures are highlighted for {comp} ({stock_code})?"
    if topic == "S":
        return f"What social and workforce initiatives are described by {comp} ({stock_code})?"
    if topic == "G":
        return f"What governance and risk controls are reported by {comp} ({stock_code})?"
    return f"What ESG-related themes are discussed in {comp} ({stock_code}) reports?"


def _normalize_text(text: str, max_len: int = 420) -> str:
    compact = " ".join(text.split())
    return compact[:max_len]


def build_triplets_from_json_zip(zip_path: Path, max_triplets: int = 2500, seed: int = 42) -> list[TripletRecord]:
    rng = random.Random(seed)

    with zipfile.ZipFile(zip_path, "r") as zf:
        json_members = [m for m in zf.namelist() if m.endswith(".json")]
        records = []
        for member in json_members:
            with zf.open(member) as fp:
                payload = json.load(fp)
                records.append(payload)

    if len(records) < 2:
        raise ValueError("JSON dataset does not contain enough records for triplet fine-tuning.")

    passages = []
    for rec in records:
        stock_code = str(rec.get("stock_code", "")).zfill(5)
        company = rec.get("company_name") or f"Company {stock_code}"
        industry = rec.get("industry") or "Unknown"
        rating = rec.get("esg_rating") or "N/A"
        strengths = rec.get("strengths") or []
        weaknesses = rec.get("weaknesses") or []

        summary = (
            f"{company} ({stock_code}) in {industry} has ESG rating {rating}. "
            f"Key strengths include: {', '.join(strengths) if strengths else 'not specified'}. "
            f"Weaknesses include: {', '.join(weaknesses) if weaknesses else 'none listed'}."
        )

        topic = classify_topic(summary)
        passages.append(
            {
                "stock_code": stock_code,
                "company_name": company,
                "topic": topic,
                "text": _normalize_text(summary, max_len=560),
                "strengths": strengths,
            }
        )

    triplets: list[TripletRecord] = []

    by_topic: dict[str, list[dict[str, Any]]] = {}
    for p in passages:
        by_topic.setdefault(p["topic"], []).append(p)

    for p in passages:
        stock_code = p["stock_code"]
        company = p["company_name"]
        topic = p["topic"]

        query_pool = []
        if p["strengths"]:
            for strength in p["strengths"]:
                query_pool.append(f"How does {company} ({stock_code}) perform on {strength.lower()}?")
        query_pool.append(_topic_query(topic, stock_code, company))

        neg_pool = [x for x in passages if x["stock_code"] != stock_code]
        if not neg_pool:
            continue

        same_topic_neg = [x for x in neg_pool if x["topic"] == topic]

        for q in query_pool:
            if same_topic_neg:
                neg = rng.choice(same_topic_neg)
            else:
                neg = rng.choice(neg_pool)

            triplets.append(
                TripletRecord(
                    query=_normalize_text(q, max_len=240),
                    positive=p["text"],
                    negative=neg["text"],
                    topic=topic,
                    stock_code=stock_code,
                    source="json_zip",
                )
            )

            if len(triplets) >= max_triplets:
                return triplets

    return triplets


def build_triplets_from_db_rows(rows: list[dict[str, Any]], max_triplets: int = 3500, seed: int = 42) -> list[TripletRecord]:
    rng = random.Random(seed)

    if len(rows) < 2:
        raise ValueError("Not enough chunk rows for DB triplet fine-tuning.")

    normalized = []
    for r in rows:
        text = _normalize_text(r["text"], max_len=560)
        topic = classify_topic(text)
        normalized.append(
            {
                "stock_code": r["stock_code"],
                "company_name": r.get("company_name") or f"Company {r['stock_code']}",
                "topic": topic,
                "text": text,
                "doc_type": r.get("doc_type", "report"),
            }
        )

    by_topic: dict[str, list[dict[str, Any]]] = {}
    by_code: dict[str, list[dict[str, Any]]] = {}
    for item in normalized:
        by_topic.setdefault(item["topic"], []).append(item)
        by_code.setdefault(item["stock_code"], []).append(item)

    triplets: list[TripletRecord] = []
    for stock_code, items in by_code.items():
        for item in items[:10]:
            topic = item["topic"]
            query = _topic_query(topic, stock_code, item["company_name"])

            same_topic = [x for x in by_topic.get(topic, []) if x["stock_code"] != stock_code]
            other_company = [x for x in normalized if x["stock_code"] != stock_code]
            if not other_company:
                continue

            negative = rng.choice(same_topic) if same_topic else rng.choice(other_company)

            triplets.append(
                TripletRecord(
                    query=query,
                    positive=item["text"],
                    negative=negative["text"],
                    topic=topic,
                    stock_code=stock_code,
                    source="db_chunks",
                )
            )

            if len(triplets) >= max_triplets:
                return triplets

    return triplets


def save_triplets_jsonl(triplets: list[TripletRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for t in triplets:
            f.write(json.dumps(asdict(t), ensure_ascii=False) + "\n")


def _triplet_accuracy(model, triplets: list[TripletRecord]) -> float:
    import numpy as np

    if not triplets:
        return 0.0

    queries = [t.query for t in triplets]
    positives = [t.positive for t in triplets]
    negatives = [t.negative for t in triplets]

    q_emb = model.encode(queries, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False)
    p_emb = model.encode(positives, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False)
    n_emb = model.encode(negatives, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False)

    pos_sim = np.sum(q_emb * p_emb, axis=1)
    neg_sim = np.sum(q_emb * n_emb, axis=1)
    return float(np.mean(pos_sim > neg_sim))


def _hash_features(text: str, dim: int = 2048) -> list[float]:
    import hashlib
    import math

    tokens = re.findall(r"[a-zA-Z]{3,}", text.lower())
    if not tokens:
        return [0.0] * dim

    vec = [0.0] * dim
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:4], "big") % dim
        sign = 1.0 if (digest[4] % 2 == 0) else -1.0
        vec[idx] += sign

    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _hash_triplet_accuracy(model, triplets: list[TripletRecord], dim: int, device: str = "cpu") -> float:
    import torch
    import torch.nn.functional as F

    if not triplets:
        return 0.0

    model.eval()
    correct = 0
    with torch.no_grad():
        for t in triplets:
            q = torch.tensor(_hash_features(t.query, dim=dim), dtype=torch.float32, device=device).unsqueeze(0)
            p = torch.tensor(_hash_features(t.positive, dim=dim), dtype=torch.float32, device=device).unsqueeze(0)
            n = torch.tensor(_hash_features(t.negative, dim=dim), dtype=torch.float32, device=device).unsqueeze(0)
            qv = F.normalize(model(q), p=2, dim=1)
            pv = F.normalize(model(p), p=2, dim=1)
            nv = F.normalize(model(n), p=2, dim=1)
            pos = torch.sum(qv * pv, dim=1).item()
            neg = torch.sum(qv * nv, dim=1).item()
            if pos > neg:
                correct += 1
    return correct / len(triplets)


def _train_hash_triplet_model(
    triplets: list[TripletRecord],
    output_dir: Path,
    epochs: int,
    batch_size: int,
    lr: float,
    seed: int,
) -> FinetuneReport:
    import numpy as np
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    torch.manual_seed(seed)
    random.seed(seed)

    class HashEncoder(nn.Module):
        def __init__(self, input_dim: int = 2048, embed_dim: int = 256) -> None:
            super().__init__()
            self.layers = nn.Sequential(
                nn.Linear(input_dim, 768),
                nn.ReLU(),
                nn.Linear(768, embed_dim),
            )

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return self.layers(x)

    dim = 2048
    rng = random.Random(seed)
    shuffled = triplets[:]
    rng.shuffle(shuffled)

    split_idx = int(len(shuffled) * 0.9)
    train_triplets = shuffled[:split_idx]
    val_triplets = shuffled[split_idx:] or shuffled[: min(100, len(shuffled))]

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = HashEncoder(input_dim=dim, embed_dim=256).to(device)

    baseline_acc = _hash_triplet_accuracy(model, val_triplets, dim=dim, device=device)

    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.TripletMarginWithDistanceLoss(
        distance_function=lambda x, y: 1.0 - F.cosine_similarity(x, y), margin=0.2
    )

    for _ in range(epochs):
        rng.shuffle(train_triplets)
        model.train()
        for start in range(0, len(train_triplets), batch_size):
            batch = train_triplets[start : start + batch_size]
            q = np.array([_hash_features(t.query, dim=dim) for t in batch], dtype=np.float32)
            p = np.array([_hash_features(t.positive, dim=dim) for t in batch], dtype=np.float32)
            n = np.array([_hash_features(t.negative, dim=dim) for t in batch], dtype=np.float32)

            q_t = torch.tensor(q, device=device)
            p_t = torch.tensor(p, device=device)
            n_t = torch.tensor(n, device=device)

            qv = F.normalize(model(q_t), p=2, dim=1)
            pv = F.normalize(model(p_t), p=2, dim=1)
            nv = F.normalize(model(n_t), p=2, dim=1)

            loss = criterion(qv, pv, nv)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

    tuned_acc = _hash_triplet_accuracy(model, val_triplets, dim=dim, device=device)

    output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = output_dir / "hash_triplet_encoder.pt"
    metadata_path = output_dir / "hash_triplet_encoder_meta.json"

    torch.save(model.state_dict(), checkpoint_path)
    metadata_path.write_text(
        json.dumps(
            {
                "input_dim": dim,
                "embed_dim": 256,
                "device_trained": device,
                "note": "Offline fallback retriever training with triplet loss on hashed text features.",
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    return FinetuneReport(
        source=train_triplets[0].source,
        training_backend="offline_hash_triplet",
        model_name="hash-triplet-encoder",
        output_dir=str(output_dir),
        triplet_count=len(triplets),
        train_triplets=len(train_triplets),
        val_triplets=len(val_triplets),
        epochs=epochs,
        batch_size=batch_size,
        lr=lr,
        baseline_triplet_accuracy=round(baseline_acc, 4),
        tuned_triplet_accuracy=round(tuned_acc, 4),
    )


def train_retriever_triplet_model(
    triplets: list[TripletRecord],
    model_name: str,
    output_dir: Path,
    epochs: int = 1,
    batch_size: int = 24,
    lr: float = 2e-5,
    seed: int = 42,
) -> FinetuneReport:
    if len(triplets) < 30:
        raise ValueError("Need at least 30 triplets for meaningful retriever fine-tuning.")

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        from sentence_transformers import InputExample, SentenceTransformer, losses
        from torch.utils.data import DataLoader
    except Exception:
        return _train_hash_triplet_model(
            triplets=triplets,
            output_dir=output_dir,
            epochs=epochs,
            batch_size=batch_size,
            lr=lr,
            seed=seed,
        )

    rng = random.Random(seed)
    shuffled = triplets[:]
    rng.shuffle(shuffled)

    split_idx = int(len(shuffled) * 0.9)
    train_triplets = shuffled[:split_idx]
    val_triplets = shuffled[split_idx:] or shuffled[: min(100, len(shuffled))]

    try:
        base_model = SentenceTransformer(model_name)
    except Exception:
        return _train_hash_triplet_model(
            triplets=triplets,
            output_dir=output_dir,
            epochs=epochs,
            batch_size=batch_size,
            lr=lr,
            seed=seed,
        )

    baseline_acc = _triplet_accuracy(base_model, val_triplets)

    train_examples = [InputExample(texts=[t.query, t.positive, t.negative]) for t in train_triplets]
    loader = DataLoader(train_examples, shuffle=True, batch_size=batch_size)
    train_loss = losses.TripletLoss(model=base_model, triplet_margin=0.18)

    warmup_steps = max(1, int(len(loader) * epochs * 0.1))

    base_model.fit(
        train_objectives=[(loader, train_loss)],
        epochs=epochs,
        warmup_steps=warmup_steps,
        output_path=str(output_dir),
        optimizer_params={"lr": lr},
        show_progress_bar=True,
    )

    tuned_model = SentenceTransformer(str(output_dir))
    tuned_acc = _triplet_accuracy(tuned_model, val_triplets)

    return FinetuneReport(
        source=train_triplets[0].source,
        training_backend="sentence_transformers_triplet",
        model_name=model_name,
        output_dir=str(output_dir),
        triplet_count=len(triplets),
        train_triplets=len(train_triplets),
        val_triplets=len(val_triplets),
        epochs=epochs,
        batch_size=batch_size,
        lr=lr,
        baseline_triplet_accuracy=round(baseline_acc, 4),
        tuned_triplet_accuracy=round(tuned_acc, 4),
    )
