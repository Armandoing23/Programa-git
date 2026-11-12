from __future__ import annotations

from dataclasses import asdict
from typing import Dict, List, Optional

from brain.critic import Critic
from brain.knowledge_graph import KnowledgeGraph
from brain.memory import Memory
from brain.reasoning import Hypothesis, ReasoningEngine
from utils import truncate


class Brain:
    def __init__(self, graph: KnowledgeGraph, memory: Optional[Memory] = None) -> None:
        self.graph = graph
        self.reasoning = ReasoningEngine(graph)
        self.critic = Critic(graph)
        self.memory = memory

    def _to_dict(self, h: Hypothesis) -> dict:
        d = asdict(h)
        if self.memory:
            learned = {}
            for token in [h.pathogen, *h.drugs, *h.targets]:
                bias = self.memory.bias_for(token)
                if bias:
                    learned[token] = round(bias, 3)
            if learned:
                d["learned"] = learned
        return d

    def analyze(self, query: str, entities: List[str]) -> dict:
        pathogen = self.reasoning.resolve_pathogen(query, entities)
        if not pathogen:
            return {
                "mode": "analyze",
                "pathogen": None,
                "candidates": [],
                "combinations": [],
                "evaluated": [],
                "comparison": [],
                "summary": "No se identificó un patógeno conocido en la consulta.",
            }
        candidates = self.reasoning.generate_candidates(pathogen)
        ranked = self.critic.rank(candidates)
        out = [self._to_dict(h) for h, _ in ranked]
        if self.memory:
            out = self.memory.apply_learning(out)
            for h in out:
                self.memory.remember_hypothesis(h)
        return {
            "mode": "analyze",
            "pathogen": pathogen,
            "pathogen_label": self.graph.nodes[f"P:{pathogen}"].label,
            "candidates": out,
            "combinations": [],
            "evaluated": [],
            "comparison": [],
            "summary": f"Generadas {len(out)} hipótesis de candidatos para {self.graph.nodes[f'P:{pathogen}'].label}.",
        }

    def evaluate(self, drug: str, target: str) -> dict:
        h = self.reasoning.evaluate(drug, target)
        c = self.critic.evaluate(h)
        d = self._to_dict(h)
        d["critique"] = asdict(c)
        if self.memory:
            self.memory.remember_hypothesis(d)
        return {"mode": "evaluate", "evaluated": [d], "summary": c.verdict}

    def combine(self, drugs: List[str], pathogen: Optional[str] = None) -> dict:
        hs = self.reasoning.generate_combinations(drugs, pathogen)
        ranked = self.critic.rank(hs)
        out = [self._to_dict(h) for h, _ in ranked]
        if self.memory:
            out = self.memory.apply_learning(out)
            for h in out:
                self.memory.remember_hypothesis(h)
        return {"mode": "combine", "combinations": out, "summary": f"{len(out)} combinaciones evaluadas."}

    def compare(self, alternatives: List[str], pathogen: Optional[str] = None) -> dict:
        hs = self.reasoning.compare(alternatives, pathogen)
        ranked = self.critic.rank(hs)
        out = [self._to_dict(h) for h, _ in ranked]
        if self.memory:
            out = self.memory.apply_learning(out)
            for h in out:
                self.memory.remember_hypothesis(h)
        return {"mode": "compare", "comparison": out, "summary": f"{len(out)} alternativas comparadas."}

    def build_context_for_llm(self, brain_result: dict, query: str) -> str:
        lines = [f"CONSULTA: {query}", "", "RAZONAMIENTO ESTRUCTURADO (motor simbólico):"]
        for c in brain_result.get("candidates", [])[:8]:
            lines.append(f"- {c['title']} | confianza {c['confidence']} | {c['rationale']}")
        for c in brain_result.get("combinations", [])[:5]:
            lines.append(f"- {c['title']} | confianza {c['confidence']} | {c['rationale']}")
        for e in brain_result.get("evaluated", [])[:3]:
            lines.append(f"- {e['title']} | confianza {e['confidence']} | {e['rationale']}")
        for cm in brain_result.get("comparison", [])[:5]:
            lines.append(f"- {cm['title']} | confianza {cm['confidence']}")
        return truncate("\n".join(lines), 4000)
