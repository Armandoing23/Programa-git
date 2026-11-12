from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from utils import normalize, clamp

NodeType = str


@dataclass
class Node:
    id: str
    type: str
    label: str
    data: dict = field(default_factory=dict)
    aliases: Set[str] = field(default_factory=set)


@dataclass
class Edge:
    source: str
    target: str
    relation: str
    weight: float = 1.0
    meta: dict = field(default_factory=dict)


class KnowledgeGraph:
    def __init__(self, knowledge_dir: str | Path) -> None:
        self.dir = Path(knowledge_dir)
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Edge] = []
        self._adj: Dict[str, List[Edge]] = {}
        self._alias_index: Dict[str, str] = {}
        self.load()

    def _add_node(self, node_id: str, ntype: str, label: str, data: dict, aliases: List[str]) -> None:
        node = Node(id=node_id, type=ntype, label=label, data=data, aliases=set(aliases))
        self.nodes[node_id] = node
        for a in [label, *aliases]:
            na = normalize(a)
            if na:
                self._alias_index.setdefault(na, node_id)

    def _add_edge(self, source: str, target: str, relation: str, weight: float = 1.0, meta: dict | None = None) -> None:
        if source not in self.nodes or target not in self.nodes:
            return
        edge = Edge(source=source, target=target, relation=relation, weight=weight, meta=meta or {})
        self.edges.append(edge)
        self._adj.setdefault(source, []).append(edge)
        self._adj.setdefault(target, []).append(edge)

    def load(self) -> None:
        pathogens = self._read_json("pathogens.json")
        targets = self._read_json("targets.json")
        drugs = self._read_json("drugs.json")

        for key, p in (pathogens.get("pathogens") or {}).items():
            self._add_node(
                f"P:{key}", "pathogen", p.get("name", key), p,
                [key, p.get("name", ""), p.get("disease", "")] + p.get("variants", []),
            )
        for key, t in (targets.get("targets") or {}).items():
            self._add_node(
                f"T:{key}", "target", t.get("name", key), t,
                [key, t.get("name", "")],
            )
        for key, d in (drugs.get("drugs") or {}).items():
            self._add_node(
                f"D:{key}", "drug", d.get("name", key), d,
                [key, d.get("name", ""), d.get("brand", "")],
            )

        self._link_pathogens((pathogens.get("pathogens") or {}))
        self._link_targets((targets.get("targets") or {}))
        self._link_drugs((drugs.get("drugs") or {}))

    def _read_json(self, name: str) -> dict:
        path = self.dir / name
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _link_pathogens(self, pathogens: dict) -> None:
        for key, p in pathogens.items():
            pid = f"P:{key}"
            for t in p.get("targets", []):
                if f"T:{t}" in self.nodes:
                    self._add_edge(pid, f"T:{t}", "has_target")
            for sim in p.get("similar_treated", []):
                sid = f"P:{sim}"
                if sid in self.nodes:
                    self._add_edge(pid, sid, "similar_to")
            for pw in p.get("key_pathways", []):
                self._add_edge(pid, self._pathway_node(pw), "activates_pathway")

    def _link_targets(self, targets: dict) -> None:
        for key, t in targets.items():
            tid = f"T:{key}"
            for inhib in t.get("known_inhibitors", []):
                for dkey, _ in self._resolve_drug(inhib):
                    self._add_edge(f"D:{dkey}", tid, "inhibits", weight=evidence_node_weight(t))

    def _link_drugs(self, drugs: dict) -> None:
        for key, d in drugs.items():
            did = f"D:{key}"
            for t in d.get("targets", []):
                if f"T:{t}" in self.nodes:
                    self._add_edge(did, f"T:{t}", "targets")
            for syn in d.get("synergies", []):
                for dkey, _ in self._resolve_drug(syn):
                    if dkey != key:
                        self._add_edge(did, f"D:{dkey}", "synergy")
            for inter in d.get("interactions", []):
                for dkey, _ in self._resolve_drug(inter):
                    if dkey != key:
                        self._add_edge(did, f"D:{dkey}", "interaction")

    def _resolve_drug(self, alias: str) -> List[Tuple[str, str]]:
        node_id = self._alias_index.get(normalize(alias))
        if node_id and node_id.startswith("D:"):
            return [(node_id[2:], alias)]
        out = []
        for nid, node in self.nodes.items():
            if nid.startswith("D:") and normalize(alias) in node.aliases:
                out.append((nid[2:], alias))
        return out

    def _pathway_node(self, name: str) -> str:
        nid = f"PW:{normalize(name)}"
        if nid not in self.nodes:
            self._add_node(nid, "pathway", name, {}, [name])
        return nid

    def neighbors(self, node_id: str) -> List[Edge]:
        return self._adj.get(node_id, [])

    def edges_of_type(self, node_id: str, relation: str) -> List[Edge]:
        return [e for e in self._adj.get(node_id, []) if e.relation == relation]

    def resolve(self, alias: str) -> Optional[Node]:
        node_id = self._alias_index.get(normalize(alias))
        return self.nodes.get(node_id) if node_id else None

    def candidate_drugs_for_pathogen(self, pathogen_key: str) -> List[Tuple[str, float]]:
        pid = f"P:{pathogen_key}"
        if pid not in self.nodes:
            return []
        results: Dict[str, float] = {}
        for et in self.edges_of_type(pid, "has_target"):
            tid = et.target
            for ed in self.edges_of_type(tid, "inhibits") + self.edges_of_type(tid, "targets"):
                if ed.source.startswith("D:"):
                    dkey = ed.source[2:]
                    results[dkey] = max(results.get(dkey, 0.0), ed.weight)
        return sorted(results.items(), key=lambda x: x[1], reverse=True)

    def paths_drug_to_pathogen(self, drug_key: str, pathogen_key: str) -> List[List[str]]:
        start = f"D:{drug_key}"
        goal = f"P:{pathogen_key}"
        if start not in self.nodes or goal not in self.nodes:
            return []
        queue: List[List[str]] = [[start]]
        found: List[List[str]] = []
        seen = {start}
        while queue and len(found) < 5:
            path = queue.pop(0)
            current = path[-1]
            if current == goal:
                found.append(path)
                continue
            if len(path) > 4:
                continue
            for e in self._adj.get(current, []):
                nxt = e.target if e.source == current else e.source
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append(path + [nxt])
        return found

    def stats(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for n in self.nodes.values():
            counts[n.type] = counts.get(n.type, 0) + 1
        return counts


def evidence_node_weight(target_data: dict) -> float:
    level = (target_data.get("evidence_level") or "")
    from brain.scoring import evidence_to_score

    return clamp(evidence_to_score(level) + 0.1, 0.1, 1.0)
