from __future__ import annotations

from typing import Dict, List, Optional

from brain.knowledge_graph import KnowledgeGraph
from utils import normalize


class KnowledgeAnalyzer:
    def __init__(self, knowledge_dir: str = "backend/knowledge") -> None:
        self.graph = KnowledgeGraph(knowledge_dir)

    @property
    def pathogens(self) -> dict:
        return self._section("pathogens")

    @property
    def targets(self) -> dict:
        return self._section("targets")

    @property
    def drugs(self) -> dict:
        return self._section("drugs")

    def _section(self, name: str) -> dict:
        from utils import load_json
        import os
        path = self.graph.dir / f"{name}.json"
        if path.exists():
            return load_json(str(path)).get(name, {})
        return {}

    def extract_entities(self, query: str) -> List[str]:
        query_norm = normalize(query)
        query_tokens = set(t for t in query_norm.split() if len(t) >= 2)
        found: List[str] = []
        for nid, node in self.graph.nodes.items():
            if node.type not in ("pathogen", "target", "drug"):
                continue
            key = node.id.split(":", 1)[1]
            if key in found:
                continue
            matched = False
            for alias in node.aliases:
                a_norm = normalize(alias)
                if not a_norm:
                    continue
                if a_norm in query_norm or query_norm in a_norm:
                    matched = True
                    break
                a_tokens = set(t for t in a_norm.split() if len(t) >= 2)
                if a_tokens and (a_tokens & query_tokens):
                    matched = True
                    break
            if matched:
                found.append(key)
        return found

    def get_pathogen_info(self, key: str) -> Optional[dict]:
        node = self.graph.nodes.get(f"P:{key}")
        return node.data if node else None

    def get_target_info(self, key: str) -> Optional[dict]:
        node = self.graph.nodes.get(f"T:{key}")
        return node.data if node else None

    def get_drug_info(self, key: str) -> Optional[dict]:
        node = self.graph.nodes.get(f"D:{key}")
        return node.data if node else None

    def find_drugs_by_target(self, target_key: str) -> List[tuple]:
        out = []
        for nid, node in self.graph.nodes.items():
            if nid.startswith("D:") and any(e.relation in ("targets", "inhibits") and e.target == f"T:{target_key}" for e in self.graph.neighbors(nid)):
                out.append((node.id[2:], node.data))
        return out

    def find_targets_by_pathogen(self, pathogen_key: str) -> List[str]:
        return [e.target[2:] for e in self.graph.edges_of_type(f"P:{pathogen_key}", "has_target")]

    def find_drugs_by_pathogen(self, pathogen_key: str) -> List[tuple]:
        seen = set()
        out = []
        for dkey, _ in self.graph.candidate_drugs_for_pathogen(pathogen_key):
            if dkey not in seen:
                seen.add(dkey)
                node = self.graph.nodes.get(f"D:{dkey}")
                if node:
                    out.append((dkey, node.data))
        return out

    def build_knowledge_context(self, query: str, entities: List[str]) -> str:
        lines = ["=== KNOWLEDGE BASE CONTEXT ==="]
        for key in entities:
            p = self.get_pathogen_info(key)
            if p:
                lines.append(f"PATHOGEN: {p.get('name', key)} | Familia: {p.get('family')} | Mecanismo: {p.get('mechanism')}")
            t = self.get_target_info(key)
            if t:
                lines.append(f"TARGET: {t.get('name', key)} | Función: {t.get('function')} | Evidencia: {t.get('evidence_level')}")
            d = self.get_drug_info(key)
            if d:
                lines.append(f"DRUG: {d.get('name', key)} | Clase: {d.get('class')} | Dianas: {', '.join(d.get('targets', []))} | Evidencia: {d.get('evidence_level')}")
        if len(lines) == 1:
            return "Sin entidades coincidentes en la base. Usa razonamiento biomédico general."
        return "\n".join(lines)
