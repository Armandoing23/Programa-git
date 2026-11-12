from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from brain.knowledge_graph import KnowledgeGraph
from brain.scoring import evidence_to_score, approval_to_score
from utils import clamp, normalize


@dataclass
class Hypothesis:
    id: str
    kind: str
    title: str
    pathogen: Optional[str]
    targets: List[str] = field(default_factory=list)
    drugs: List[str] = field(default_factory=list)
    confidence: float = 0.0
    evidence_scores: List[float] = field(default_factory=list)
    rationale: str = ""
    risks: List[str] = field(default_factory=list)
    gaps: List[str] = field(default_factory=list)
    next_steps: List[str] = field(default_factory=list)
    meta: dict = field(default_factory=dict)


class ReasoningEngine:
    def __init__(self, graph: KnowledgeGraph) -> None:
        self.graph = graph

    def resolve_pathogen(self, query: str, entities: List[str]) -> Optional[str]:
        for key in entities:
            if f"P:{key}" in self.graph.nodes:
                return key
        node = self.graph.resolve(query)
        if node and node.type == "pathogen":
            return node.id[2:]
        return None

    def generate_candidates(self, pathogen_key: str) -> List[Hypothesis]:
        pid = f"P:{pathogen_key}"
        if pid not in self.graph.nodes:
            return []
        pnode = self.graph.nodes[pid]
        targets = [e.target[2:] for e in self.graph.edges_of_type(pid, "has_target")]
        candidates = self.graph.candidate_drugs_for_pathogen(pathogen_key)
        hypotheses: List[Hypothesis] = []

        if not candidates:
            hypotheses.append(
                Hypothesis(
                    id=f"cand:{pathogen_key}:none",
                    kind="candidate",
                    title=f"Sin candidatos directos en la base para {pnode.label}",
                    pathogen=pathogen_key,
                    targets=targets,
                    confidence=0.05,
                    rationale="No se encontraron fármacos mapeados a las dianas del patógeno.",
                    gaps=["Ampliar base de fármacos y dianas."],
                    next_steps=["Revisión bibliográfica dirigida a dianas no cubiertas."],
                )
            )
            return hypotheses

        for dkey, weight in candidates[:12]:
            dnode = self.graph.nodes[f"D:{dkey}"]
            ddata = dnode.data
            covered = [
                t for t in targets
                if self._drug_hits_target(dkey, t)
            ]
            ev = evidence_to_score(ddata.get("evidence_level"))
            appr = approval_to_score(ddata.get("approval_status"))
            conf = clamp(0.45 * ev + 0.3 * appr + 0.25 * weight, 0.05, 0.98)
            risks = list(ddata.get("risks", []))
            hypotheses.append(
                Hypothesis(
                    id=f"cand:{pathogen_key}:{dkey}",
                    kind="candidate",
                    title=f"{dnode.label} contra {pnode.label}",
                    pathogen=pathogen_key,
                    targets=covered or targets[:1],
                    drugs=[dkey],
                    confidence=round(conf, 3),
                    evidence_scores=[round(ev, 3), round(appr, 3)],
                    rationale=(
                        f"{dnode.label} ({ddata.get('class', 'N/A')}) actúa vía "
                        f"{', '.join(covered) or ddata.get('mechanism', 'mecanismo descrito')}. "
                        f"Nivel de evidencia: {ddata.get('evidence_level', 'N/A')}."
                    ),
                    risks=risks,
                    gaps=self._gaps_for(covered, targets),
                    next_steps=self._next_steps(ddata),
                    meta={"approval": ddata.get("approval_status"), "class": ddata.get("class")},
                )
            )
        hypotheses.sort(key=lambda h: h.confidence, reverse=True)
        return hypotheses

    def generate_combinations(self, drugs: List[str], pathogen_key: Optional[str] = None) -> List[Hypothesis]:
        resolved = [(self.graph.resolve(d), d) for d in drugs]
        resolved = [(n, orig) for n, orig in resolved if n and n.type == "drug"]
        if len(resolved) < 2:
            return []
        combos: List[Hypothesis] = []
        for i in range(len(resolved)):
            for j in range(i + 1, len(resolved)):
                a, b = resolved[i][0], resolved[j][0]
                synergy = any(e.relation == "synergy" for e in self.graph._adj.get(a.id, []) if e.source == b.id or e.target == b.id)
                interaction = any(e.relation == "interaction" for e in self.graph._adj.get(a.id, []) if e.source == b.id or e.target == b.id)
                ev_a = evidence_to_score(a.data.get("evidence_level"))
                ev_b = evidence_to_score(b.data.get("evidence_level"))
                base = (ev_a + ev_b) / 2
                if synergy:
                    conf = clamp(base + 0.2, 0.1, 0.98)
                    ratio = "Sinergia documentada en la base de conocimiento."
                elif interaction:
                    conf = clamp(base - 0.25, 0.05, 0.95)
                    ratio = "Interacción documentada: requiere precaución o monitorización."
                else:
                    conf = clamp(base * 0.85, 0.05, 0.9)
                    ratio = "Mecanismos complementarios; sinergia hipotética no confirmada en la base."
                combo_targets = []
                for node in (a, b):
                    for e in self.graph.edges_of_type(node.id, "targets"):
                        combo_targets.append(e.target[2:])
                combos.append(
                    Hypothesis(
                        id=f"combo:{a.id[2:]}:{b.id[2:]}",
                        kind="combination",
                        title=f"{a.label} + {b.label}",
                        pathogen=pathogen_key,
                        drugs=[a.id[2:], b.id[2:]],
                        targets=combo_targets[:4],
                        confidence=round(conf, 3),
                        evidence_scores=[round(ev_a, 3), round(ev_b, 3)],
                        rationale=ratio,
                        risks=list(a.data.get("risks", [])) + list(b.data.get("risks", [])),
                        gaps=[] if synergy else ["Validar sinergia in vitro."],
                        next_steps=["Ensayo de sinergia (Chou-Talalay) en líneas celulares."],
                        meta={"synergy": synergy, "interaction": interaction},
                    )
                )
        combos.sort(key=lambda h: h.confidence, reverse=True)
        return combos

    def evaluate(self, drug_key: str, target_key: str) -> Hypothesis:
        dnode = self.graph.nodes.get(f"D:{drug_key}")
        tnode = self.graph.nodes.get(f"T:{target_key}")
        hits = self._drug_hits_target(drug_key, target_key)
        ev = evidence_to_score(dnode.data.get("evidence_level")) if dnode else 0.05
        conf = clamp(0.4 + 0.5 * ev + (0.1 if hits else -0.2), 0.05, 0.98)
        return Hypothesis(
            id=f"eval:{drug_key}:{target_key}",
            kind="evaluation",
            title=f"Evaluación: {dnode.label if dnode else drug_key} vs {tnode.label if tnode else target_key}",
            pathogen=None,
            targets=[target_key] if tnode else [],
            drugs=[drug_key] if dnode else [],
            confidence=round(conf, 3),
            evidence_scores=[round(ev, 3)],
            rationale=(
                f"El fármaco {'apunta directamente' if hits else 'no está mapeado directamente'} a la diana en la base. "
                f"{dnode.data.get('mechanism', '') if dnode else ''}"
            ),
            risks=list(dnode.data.get("risks", [])) if dnode else ["Fármaco no encontrado en la base."],
            gaps=[] if hits else ["Confirmar unión fármaco-diana experimentalmente."],
            next_steps=["Ensayo de unión (SPR/BLI) y actividad en ensayo celular."],
            meta={"direct_hit": hits},
        )

    def compare(self, alternatives: List[str], pathogen_key: Optional[str] = None) -> List[Hypothesis]:
        result: List[Hypothesis] = []
        for alt in alternatives:
            node = self.graph.resolve(alt)
            if not node or node.type != "drug":
                continue
            ev = evidence_to_score(node.data.get("evidence_level"))
            appr = approval_to_score(node.data.get("approval_status"))
            conf = clamp(0.5 * ev + 0.5 * appr, 0.05, 0.98)
            result.append(
                Hypothesis(
                    id=f"cmp:{node.id[2:]}",
                    kind="comparison",
                    title=f"Comparativa: {node.label}",
                    pathogen=pathogen_key,
                    drugs=[node.id[2:]],
                    confidence=round(conf, 3),
                    evidence_scores=[round(ev, 3), round(appr, 3)],
                    rationale=f"Clase {node.data.get('class', 'N/A')}; aprobación {node.data.get('approval_status', 'N/A')}.",
                    risks=list(node.data.get("risks", [])),
                    gaps=[],
                    next_steps=["Comparar en ensayo clínico head-to-head."],
                    meta={"approval": node.data.get("approval_status")},
                )
            )
        result.sort(key=lambda h: h.confidence, reverse=True)
        return result

    def _drug_hits_target(self, drug_key: str, target_key: str):
        did = f"D:{drug_key}"
        for e in self.graph.edges_of_type(did, "targets"):
            if e.target == f"T:{target_key}":
                return True
        return False

    def _gaps_for(self, covered: List[str], all_targets: List[str]) -> List[str]:
        missing = [t for t in all_targets if t not in covered]
        if not missing:
            return []
        return [f"Diana {m} sin fármaco mapeado directamente." for m in missing[:3]]

    def _next_steps(self, ddata: dict) -> List[str]:
        steps = ["Validación in vitro de actividad."]
        if approval_to_score(ddata.get("approval_status")) < 1.0:
            steps.append("Avanzar fase clínica / reposicionamiento regulado.")
        steps.append("Evaluar resistencia emergente y barrier biofísica.")
        return steps
