from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from brain.reasoning import Hypothesis
from brain.knowledge_graph import KnowledgeGraph
from utils import clamp


@dataclass
class Critique:
    hypothesis_id: str
    score: float
    issues: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    adjustments: Dict[str, float] = field(default_factory=dict)
    verdict: str = ""


class Critic:
    def __init__(self, graph: KnowledgeGraph) -> None:
        self.graph = graph

    def evaluate(self, h: Hypothesis) -> Critique:
        issues: List[str] = []
        strengths: List[str] = []
        adj = 0.0

        if h.confidence >= 0.7:
            strengths.append("Alta confianza por evidencia/aprobación sólida.")
        elif h.confidence < 0.4:
            issues.append("Confianza baja: evidencia o cobertura insuficiente.")
            adj -= 0.05

        if h.kind == "combination":
            synergy = h.meta.get("synergy")
            interaction = h.meta.get("interaction")
            if interaction:
                issues.append("Combinación con interacción conocida: riesgo clínico.")
                adj -= 0.1
            elif synergy:
                strengths.append("Sinergia documentada en la base.")
                adj += 0.05

        if h.risks:
            if len(h.risks) >= 3:
                issues.append("Múltiples riesgos identificados; ponderar beneficio/riesgo.")
                adj -= 0.03
            else:
                strengths.append("Perfil de riesgo acotado.")
        else:
            issues.append("Sin datos de riesgo registrados.")
            adj -= 0.02

        if h.gaps:
            issues.append("Vacíos de evidencia: " + "; ".join(h.gaps[:2]))
            adj -= 0.02

        if h.meta.get("approval") and "approved" in str(h.meta.get("approval")).lower():
            strengths.append("Fármaco con aprobación regulatoria.")

        score = clamp(h.confidence + adj, 0.03, 0.99)
        verdict = "Prometedor" if score >= 0.6 else ("Requiere validación" if score >= 0.4 else "Especulativo")

        return Critique(
            hypothesis_id=h.id,
            score=round(score, 3),
            issues=issues,
            strengths=strengths,
            adjustments={"confidence_delta": round(adj, 3)},
            verdict=verdict,
        )

    def rank(self, hypotheses: List[Hypothesis]) -> List[tuple]:
        critiqued = [(h, self.evaluate(h)) for h in hypotheses]
        critiqued.sort(key=lambda x: x[1].score, reverse=True)
        return critiqued
