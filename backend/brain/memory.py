from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from utils import clamp


@dataclass
class Feedback:
    hypothesis_id: str
    rating: int
    note: str = ""
    correction: Optional[str] = None


class Memory:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._lock = threading.Lock()
        self.hypotheses: Dict[str, dict] = {}
        self.feedback: List[Feedback] = []
        self.weights: Dict[str, float] = {}
        self.load()

    def load(self) -> None:
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                self.hypotheses = data.get("hypotheses", {})
                self.weights = data.get("weights", {})
                for fb in data.get("feedback", []):
                    self.feedback.append(Feedback(**fb))
            except (json.JSONDecodeError, TypeError):
                pass

    def save(self) -> None:
        with self._lock:
            payload = {
                "hypotheses": self.hypotheses,
                "weights": self.weights,
                "feedback": [vars(f) for f in self.feedback],
            }
            self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def remember_hypothesis(self, h: dict) -> None:
        self.hypotheses[h["id"]] = h
        self.save()

    def record_feedback(self, fb: Feedback) -> None:
        with self._lock:
            self.feedback.append(fb)
            self._adjust_weights(fb)
        self.save()

    def _adjust_weights(self, fb: Feedback) -> None:
        for token in self._tokens_from_hypothesis(fb.hypothesis_id):
            cur = self.weights.get(token, 0.0)
            self.weights[token] = clamp(cur + 0.1 * fb.rating, -1.0, 1.0)

    @staticmethod
    def _tokens_from_hypothesis(hid: str) -> List[str]:
        parts = hid.split(":")
        return [p for p in parts if p] if len(parts) > 1 else []

    def bias_for(self, key: str) -> float:
        return self.weights.get(key, 0.0)

    def apply_learning(self, hypotheses: List[dict]) -> List[dict]:
        if not self.weights:
            return hypotheses
        for h in hypotheses:
            boost = 0.0
            for token in [h.get("pathogen"), *h.get("drugs", []), *h.get("targets", [])]:
                if token:
                    boost += 0.05 * self.bias_for(token)
            if boost:
                h["confidence"] = round(clamp(h.get("confidence", 0.0) + boost, 0.03, 0.99), 3)
                h["learned_boost"] = round(boost, 3)
        hypotheses.sort(key=lambda x: x.get("confidence", 0.0), reverse=True)
        return hypotheses

    def stats(self) -> dict:
        return {
            "stored_hypotheses": len(self.hypotheses),
            "feedback_count": len(self.feedback),
            "learned_weights": len(self.weights),
        }
