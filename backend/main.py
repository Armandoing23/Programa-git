from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

import uvicorn
from dataclasses import asdict

from config import get_config
from logging_config import logger
from llm.manager import LLMManager
from brain import Memory
from engine.analyzer import KnowledgeAnalyzer
from engine.hypothesis import HypothesisEngine

cfg = get_config()

app = FastAPI(
    title="Biomedical Research AI - Therapeutic Hypothesis Engine",
    description="Sistema de IA con razonamiento simbólico (cerebro), base de conocimiento y motor de hipótesis terapéuticas.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

memory = Memory(cfg.memory_path) if cfg.enable_memory else None
llm = LLMManager(cfg)
analyzer = KnowledgeAnalyzer(knowledge_dir=str(cfg.knowledge_dir))
engine = HypothesisEngine(knowledge_dir=str(cfg.knowledge_dir), llm=llm, memory=memory)


class QueryRequest(BaseModel):
    query: str = Field(..., description="Consulta en lenguaje natural")
    model: Optional[str] = Field(None)
    temperature: float = Field(0.3, ge=0.0, le=1.0)


class DrugEvaluateRequest(BaseModel):
    drug: str
    target: str


class CombinationRequest(BaseModel):
    drugs: List[str]
    pathogen: Optional[str] = None


class ComparisonRequest(BaseModel):
    alternatives: List[str]
    pathogen: Optional[str] = None


class FeedbackRequest(BaseModel):
    hypothesis_id: str
    rating: int = Field(..., ge=-1, le=1, description="-1 negativo, 1 positivo")
    note: str = ""
    correction: Optional[str] = None


class StreamRequest(BaseModel):
    mode: str = "analyze"
    query: Optional[str] = None
    drug: Optional[str] = None
    target: Optional[str] = None
    drugs: List[str] = []
    alternatives: List[str] = []
    pathogen: Optional[str] = None
    model: Optional[str] = None
    temperature: float = Field(0.3, ge=0.0, le=1.0)


def _sse(event: str, data: Any) -> str:
    import json as _json
    return f"event: {event}\ndata: {_json.dumps(data, ensure_ascii=False)}\n\n"


@app.post("/api/stream")
def stream_endpoint(req: StreamRequest):
    def event_gen():
        try:
            if req.model:
                llm.primary.model = req.model
            if req.mode == "evaluate" and (not analyzer.get_drug_info(req.drug or "") and not analyzer.graph.resolve(req.drug or "")):
                yield _sse("error", {"detail": f"Fármaco no encontrado: {req.drug}"})
                return
            brain, context, _ = engine.prepare(
                req.mode, req.query, req.drug, req.target, req.drugs, req.alternatives, req.pathogen
            )
            yield _sse("brain", brain)
            if req.mode == "evaluate":
                q = f"Evaluar {req.drug} contra {req.target}"
            elif req.mode == "combine":
                q = f"Combinar {', '.join(req.drugs)}"
            elif req.mode == "compare":
                q = f"Comparar {', '.join(req.alternatives)}"
            else:
                q = req.query or ""
            for token in engine.narrative_stream(q, context, brain, req.temperature):
                yield _sse("token", {"text": token})
            yield _sse("done", {"success": True})
        except Exception as e:
            logger.exception("Error en streaming")
            yield _sse("error", {"detail": str(e)})

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@app.get("/api/status")
def get_status():
    return {
        "status": "running",
        "version": "2.0.0",
        "provider": cfg.provider,
        "llm_available": llm.available,
        "models": llm.list_models(),
        "active_model": llm.primary.model,
        "graph_stats": analyzer.graph.stats(),
        "memory_stats": memory.stats() if memory else None,
    }


@app.post("/api/analyze")
def analyze_query(req: QueryRequest):
    try:
        if req.model:
            llm.primary.model = req.model
        return {"success": True, "data": engine.process_query(req.query, req.temperature)}
    except Exception as e:
        logger.exception("Error en /api/analyze")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/evaluate")
def evaluate(req: DrugEvaluateRequest):
    try:
        if not analyzer.get_drug_info(req.drug) and not analyzer.graph.resolve(req.drug):
            raise HTTPException(status_code=404, detail=f"Fármaco no encontrado: {req.drug}")
        result = engine.evaluate_drug(req.drug, req.target)
        return {"success": True, "data": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error en /api/evaluate")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/combinations")
def combinations(req: CombinationRequest):
    try:
        return {"success": True, "data": engine.combine_drugs(req.drugs, req.pathogen)}
    except Exception as e:
        logger.exception("Error en /api/combinations")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/compare")
def compare(req: ComparisonRequest):
    try:
        return {"success": True, "data": engine.compare_alternatives(req.alternatives, req.pathogen)}
    except Exception as e:
        logger.exception("Error en /api/compare")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/feedback")
def feedback(req: FeedbackRequest):
    if not memory:
        raise HTTPException(status_code=409, detail="Memoria deshabilitada")
    from brain.memory import Feedback
    memory.record_feedback(Feedback(req.hypothesis_id, req.rating, req.note, req.correction))
    return {"success": True, "memory_stats": memory.stats()}


@app.get("/api/memory")
def get_memory():
    if not memory:
        raise HTTPException(status_code=409, detail="Memoria deshabilitada")
    return {"success": True, "stats": memory.stats(), "weights": memory.weights}


@app.get("/api/graph")
def get_graph():
    nodes = [{"id": n.id, "type": n.type, "label": n.label} for n in analyzer.graph.nodes.values()]
    edges = [{"source": e.source, "target": e.target, "relation": e.relation, "weight": e.weight} for e in analyzer.graph.edges]
    return {"success": True, "nodes": nodes, "edges": edges}


@app.get("/api/knowledge/pathogens")
def list_pathogens():
    return {"pathogens": list(analyzer.pathogens.keys())}


@app.get("/api/knowledge/targets")
def list_targets():
    return {"targets": list(analyzer.targets.keys())}


@app.get("/api/knowledge/drugs")
def list_drugs():
    return {"drugs": list(analyzer.drugs.keys())}


@app.get("/api/knowledge/pathogen/{key}")
def get_pathogen(key: str):
    data = analyzer.get_pathogen_info(key)
    if not data:
        raise HTTPException(status_code=404, detail="Pathogen not found")
    return data


@app.get("/api/knowledge/target/{key}")
def get_target(key: str):
    data = analyzer.get_target_info(key)
    if not data:
        raise HTTPException(status_code=404, detail="Target not found")
    return data


@app.get("/api/knowledge/drug/{key}")
def get_drug(key: str):
    data = analyzer.get_drug_info(key)
    if not data:
        raise HTTPException(status_code=404, detail="Drug not found")
    return data


@app.get("/api/pathogen/{key}/candidates")
def pathogen_candidates(key: str):
    hyps = engine.brain.reasoning.generate_candidates(key)
    return {"success": True, "candidates": [asdict(h) for h in hyps]}


if __name__ == "__main__":
    logger.info("Iniciando Biomedical Research AI v2 en %s:%s", cfg.host, cfg.port)
    uvicorn.run(app, host=cfg.host, port=cfg.port)
