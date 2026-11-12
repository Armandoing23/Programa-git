from __future__ import annotations

from typing import Dict

EVIDENCE_WEIGHTS: Dict[str, float] = {
    "high": 0.92,
    "high (phase 3)": 0.92,
    "phase 3": 0.88,
    "phase 2": 0.7,
    "phase 1": 0.55,
    "medium": 0.6,
    "preclinical": 0.4,
    "in vitro": 0.35,
    "low": 0.3,
    "computational": 0.2,
    "theoretical": 0.15,
    "none": 0.05,
    "n/a": 0.05,
}


def evidence_to_score(level: str | None) -> float:
    if not level:
        return EVIDENCE_WEIGHTS["none"]
    key = str(level).strip().lower()
    if key in EVIDENCE_WEIGHTS:
        return EVIDENCE_WEIGHTS[key]
    for known, value in EVIDENCE_WEIGHTS.items():
        if known != "none" and known in key:
            return value
    return EVIDENCE_WEIGHTS["none"]


def approval_to_score(status: str | None) -> float:
    if not status:
        return 0.3
    s = str(status).lower()
    if "approved" in s:
        return 1.0
    if "investigational" in s or "phase" in s:
        return 0.6
    if "preclinical" in s:
        return 0.3
    return 0.3
