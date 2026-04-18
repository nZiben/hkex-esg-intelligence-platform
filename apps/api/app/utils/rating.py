from __future__ import annotations

import re

_BASE_MAP = {
    "AAA": 9.0,
    "AA+": 8.5,
    "AA": 8.0,
    "AA-": 7.5,
    "A+": 7.0,
    "A": 6.5,
    "A-": 6.0,
    "BBB+": 5.5,
    "BBB": 5.0,
    "BBB-": 4.5,
}


def rating_to_ordinal(rating: str | None) -> float | None:
    if not rating:
        return None
    canonical = re.sub(r"\s*\(.*?\)", "", rating).strip().upper()
    return _BASE_MAP.get(canonical)


def ordinal_to_rating(score: float) -> str:
    if score >= 8.75:
        return "AAA"
    if score >= 8.25:
        return "AA+"
    if score >= 7.75:
        return "AA"
    if score >= 7.25:
        return "AA-"
    if score >= 6.75:
        return "A+"
    if score >= 6.25:
        return "A"
    if score >= 5.75:
        return "A-"
    if score >= 5.25:
        return "BBB+"
    if score >= 4.75:
        return "BBB"
    return "BBB-"
