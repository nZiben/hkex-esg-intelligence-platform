from __future__ import annotations

import numpy as np


def build_feature_vector(topic_counts: dict[str, int], density: float, keyword_count: int) -> np.ndarray:
    e = topic_counts.get("E", 0)
    s = topic_counts.get("S", 0)
    g = topic_counts.get("G", 0)
    m = topic_counts.get("Mixed", 0)
    total = max(e + s + g + m, 1)

    return np.array(
        [
            e,
            s,
            g,
            m,
            e / total,
            s / total,
            g / total,
            density,
            keyword_count,
        ],
        dtype=float,
    )
