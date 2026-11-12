from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger("biomed_ai")


def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def tokenize(text: str) -> List[str]:
    return [t for t in normalize(text).split() if t]


def fuzzy_match(query: str, candidates: List[str], threshold: float = 0.6) -> List[str]:
    q = normalize(query)
    if not q:
        return []
    q_tokens = set(tokenize(q))
    scored: List[tuple] = []
    for cand in candidates:
        c = normalize(cand)
        if not c:
            continue
        if q in c or c in q:
            scored.append((1.0, cand))
            continue
        c_tokens = set(tokenize(c))
        if not c_tokens or not q_tokens:
            continue
        inter = len(q_tokens & c_tokens)
        union = len(q_tokens | c_tokens)
        jaccard = inter / union if union else 0.0
        if jaccard >= threshold:
            scored.append((jaccard, cand))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored]


def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def safe_json_dumps(obj: Any, **kwargs: Any) -> str:
    kwargs.setdefault("ensure_ascii", False)
    kwargs.setdefault("indent", 2)
    return json.dumps(obj, default=str, **kwargs)


def extract_json_block(text: str) -> Optional[Dict[str, Any]]:
    try:
        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if fenced:
            return json.loads(fenced.group(1))
        brace = re.search(r"\{.*\}", text, re.DOTALL)
        if brace:
            return json.loads(brace.group(0))
    except (json.JSONDecodeError, ValueError):
        return None
    return None


def truncate(text: str, limit: int = 4000) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."
