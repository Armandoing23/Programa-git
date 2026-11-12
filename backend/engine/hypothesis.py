from __future__ import annotations

from typing import Dict, List, Optional

from brain import Brain, Memory
from engine.analyzer import KnowledgeAnalyzer
from llm.manager import LLMManager


class HypothesisEngine:
    def __init__(self, knowledge_dir: str = "backend/knowledge", llm: Optional[LLMManager] = None, memory: Optional[Memory] = None) -> None:
        self.analyzer = KnowledgeAnalyzer(knowledge_dir)
        self.llm = llm
        self.memory = memory
        self.brain = Brain(self.analyzer.graph, memory)

    def _system_prompt(self) -> str:
        return (
            "Eres un motor de investigación biomédica que genera hipótesis terapéuticas "
            "a partir de una base de conocimiento estructurada y razonamiento simbólico. "
            "Reglas: (1) No reemplazas validación experimental ni aprobación regulatoria. "
            "(2) Incluye siempre la salvaguarda: 'Hipótesis computacional; requiere validación experimental y supervisión profesional.' "
            "(3) No inventes datos ni des dosis clínicas. (4) Cita la evidencia disponible. "
            "(5) Si falta evidencia, decláralo explícitamente. "
            "Formato: 1) Resumen 2) Dianas 3) Candidatos (tabla) 4) Hipótesis de combinación 5) Confianza/vacíos 6) Próximos pasos 7) Salvaguarda."
        )

    def process_query(self, query: str, temperature: float = 0.3) -> Dict:
        entities = self.analyzer.extract_entities(query)
        brain_result = self.brain.analyze(query, entities)
        return self._augment(query, entities, brain_result, temperature, mode="analyze")

    def evaluate_drug(self, drug: str, target: str, temperature: float = 0.3) -> Dict:
        brain_result = self.brain.evaluate(drug, target)
        return self._augment(f"Evaluar {drug} contra {target}", [drug, target], brain_result, temperature, mode="evaluate")

    def combine_drugs(self, drugs: List[str], pathogen: Optional[str] = None, temperature: float = 0.3) -> Dict:
        brain_result = self.brain.combine(drugs, pathogen)
        return self._augment(f"Combinar {', '.join(drugs)}", drugs, brain_result, temperature, mode="combine")

    def compare_alternatives(self, alternatives: List[str], pathogen: Optional[str] = None, temperature: float = 0.3) -> Dict:
        brain_result = self.brain.compare(alternatives, pathogen)
        return self._augment(f"Comparar {', '.join(alternatives)}", alternatives, brain_result, temperature, mode="compare")

    def _build_prompt(self, query: str, context: str, brain_result: Dict) -> str:
        return (
            f"USER QUERY: {query}\n\n"
            f"=== CONTEXTO DE BASE DE CONOCIMIENTO ===\n{context}\n\n"
            f"=== RAZONAMIENTO ESTRUCTURADO DEL MOTOR ===\n{self.brain.build_context_for_llm(brain_result, query)}\n\n"
            "Integra el razonamiento estructurado con tu conocimiento biomédico. "
            "NO contradigas los datos de la base. Sé conciso y cumple el formato obligatorio."
        )

    def _augment(self, query: str, entities: List[str], brain_result: Dict, temperature: float, mode: str) -> Dict:
        context = self.analyzer.build_knowledge_context(query, entities)
        structured = brain_result
        llm_text = ""
        llm_success = False
        llm_error = None

        if self.llm and self.llm.available:
            prompt = self._build_prompt(query, context, brain_result)
            resp = self.llm.generate(prompt, self._system_prompt(), temperature, 3000)
            llm_success = resp.success
            llm_text = resp.text
            llm_error = resp.error

        if not llm_success:
            llm_text = self._fallback_narrative(brain_result)

        return {
            "query": query,
            "mode": mode,
            "entities": entities,
            "brain": structured,
            "llm_response": llm_text,
            "llm_success": llm_success,
            "llm_error": llm_error,
        }

    def prepare(self, mode: str, query: Optional[str] = None, drug: Optional[str] = None,
                target: Optional[str] = None, drugs: Optional[List[str]] = None,
                alternatives: Optional[List[str]] = None, pathogen: Optional[str] = None):
        entities = self.analyzer.extract_entities(query or "")
        if mode == "evaluate":
            brain_result = self.brain.evaluate(drug, target)
        elif mode == "combine":
            brain_result = self.brain.combine(drugs or [], pathogen)
        elif mode == "compare":
            brain_result = self.brain.compare(alternatives or [], pathogen)
        else:
            brain_result = self.brain.analyze(query or "", entities)
        context = self.analyzer.build_knowledge_context(query or "", entities)
        return brain_result, context, entities

    def narrative_stream(self, query: str, context: str, brain_result: Dict, temperature: float = 0.3):
        if self.llm and self.llm.available:
            prompt = self._build_prompt(query, context, brain_result)
            for token in self.llm.stream(prompt, self._system_prompt(), temperature, 3000):
                yield token
        else:
            yield self._fallback_narrative(brain_result)

    def _fallback_narrative(self, brain_result: Dict) -> str:
        lines = ["[Modo base de conocimiento: el motor de IA local no está disponible]\n"]
        if brain_result.get("candidates"):
            lines.append("Candidatos terapéuticos (ordenados por confianza):")
            for c in brain_result["candidates"][:6]:
                lines.append(f"- {c['title']} | confianza {c['confidence']} | {c['rationale']}")
        if brain_result.get("combinations"):
            lines.append("Combinaciones:")
            for c in brain_result["combinations"][:4]:
                lines.append(f"- {c['title']} | confianza {c['confidence']} | {c['rationale']}")
        if brain_result.get("evaluated"):
            for e in brain_result["evaluated"]:
                lines.append(f"- {e['title']} | confianza {e['confidence']} | {e['rationale']}")
        if brain_result.get("comparison"):
            lines.append("Comparativa:")
            for c in brain_result["comparison"][:6]:
                lines.append(f"- {c['title']} | confianza {c['confidence']}")
        lines.append("\nSalvaguarda: Hipótesis computacional; requiere validación experimental y supervisión profesional.")
        return "\n".join(lines)
