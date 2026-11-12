import os
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
KNOWLEDGE = str(BACKEND / "knowledge")


@pytest.fixture(scope="module")
def engine():
    from engine.hypothesis import HypothesisEngine
    return HypothesisEngine(KNOWLEDGE, llm=None, memory=None)


def test_graph_builds(engine):
    stats = engine.analyzer.graph.stats()
    assert stats.get("pathogen", 0) > 0
    assert stats.get("drug", 0) > 0
    assert stats.get("target", 0) > 0


def test_entity_resolution_spanish(engine):
    entities = engine.analyzer.extract_entities("Analiza VIH y sugiere antivirales")
    assert "HIV" in entities


def test_analyze_returns_ranked_candidates(engine):
    r = engine.process_query("Analiza el VIH y sugiere antivirales")
    cands = r["brain"]["candidates"]
    assert len(cands) > 0
    confs = [c["confidence"] for c in cands]
    assert confs == sorted(confs, reverse=True)


def test_evaluate_drug_target(engine):
    r = engine.evaluate_drug("Lenacapavir", "Capsid_CA")
    ev = r["brain"]["evaluated"][0]
    assert ev["confidence"] > 0.5
    assert ev["critique"]["verdict"]


def test_combination_detects_synergy(engine):
    r = engine.combine_drugs(["Lenacapavir", "Dolutegravir"], "HIV")
    combos = r["brain"]["combinations"]
    assert len(combos) >= 1
    assert "synergy" in combos[0]["meta"]


def test_compare_alternatives(engine):
    r = engine.compare_alternatives(["Lenacapavir", "Dolutegravir"], "HIV")
    assert len(r["brain"]["comparison"]) >= 1


def test_memory_learning(tmp_path):
    from brain.memory import Memory, Feedback
    mem = Memory(tmp_path / "memory.json")
    before = mem.bias_for("Lenacapavir")
    mem.record_feedback(Feedback("cand:HIV:Lenacapavir", 1))
    after = mem.bias_for("Lenacapavir")
    assert after > before
