from __future__ import annotations

import re
from typing import Dict, List, Tuple


_PRIORITY_TO_SCORE = {
    "low": 20,
    "medium": 45,
    "high": 70,
    "critical": 90,
}

_SCORE_TO_PRIORITY = [
    (85, "critical"),
    (65, "high"),
    (40, "medium"),
    (0, "low"),
]

_KEYWORD_WEIGHTS = {
    "critical": {
        "unconscious": 40,
        "not breathing": 45,
        "heart attack": 45,
        "severe bleeding": 35,
        "trapped": 34,
        "collapsed": 30,
        "fire": 36,
        "explosion": 45,
        "landslide": 33,
        "flood": 28,
        "child missing": 40,
        "pregnant emergency": 32,
    },
    "high": {
        "injured": 18,
        "medical emergency": 28,
        "evacuation": 20,
        "urgent": 16,
        "no oxygen": 26,
        "no water": 14,
        "no food": 12,
        "elderly": 10,
        "disabled": 12,
        "blocked road": 16,
    },
    "medium": {
        "fever": 8,
        "supplies running out": 10,
        "need medicine": 12,
        "need support": 8,
        "power cut": 8,
        "communication down": 10,
    },
}

_TYPE_BASE_SCORES = {
    "medical": 24,
    "evacuation": 20,
    "water": 15,
    "food": 12,
}


def _normalize_text(text: str | None) -> str:
    if not text:
        return ""
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    return normalized


def _keyword_hits(text: str) -> List[Tuple[str, int]]:
    hits: List[Tuple[str, int]] = []
    for _, mapping in _KEYWORD_WEIGHTS.items():
        for keyword, score in mapping.items():
            if keyword in text:
                hits.append((keyword, score))
    return hits


def priority_for_score(score: int) -> str:
    bounded = max(0, min(100, int(score)))
    for threshold, label in _SCORE_TO_PRIORITY:
        if bounded >= threshold:
            return label
    return "low"


def analyze_severity(request_type: str | None, description: str | None, user_priority: str | None) -> Dict:
    """
    Returns:
      {
        "severity_score": int,
        "suggested_priority": str,
        "auto_override": bool,
        "matched_keywords": [str],
      }
    """
    normalized_text = _normalize_text(description)
    normalized_type = (request_type or "").strip().lower()
    normalized_user_priority = (user_priority or "medium").strip().lower()

    base = _TYPE_BASE_SCORES.get(normalized_type, 10)
    user_score = _PRIORITY_TO_SCORE.get(normalized_user_priority, 45)
    hits = _keyword_hits(normalized_text)
    keyword_score = sum(score for _, score in hits)

    # Keep user input meaningful, but let model evidence dominate on strong signals.
    severity_score = int(round(base + (0.35 * user_score) + keyword_score))
    severity_score = max(0, min(100, severity_score))
    suggested_priority = priority_for_score(severity_score)
    auto_override = _PRIORITY_TO_SCORE.get(suggested_priority, 45) > user_score

    return {
        "severity_score": severity_score,
        "suggested_priority": suggested_priority,
        "auto_override": auto_override,
        "matched_keywords": [k for k, _ in hits],
    }
