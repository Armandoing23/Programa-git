from __future__ import annotations

from typing import Dict, Iterator, List, Optional

import requests

from llm.base import BaseLLM, LLMResponse
from utils import logger


class OllamaLLM(BaseLLM):
    def __init__(self, base_url: str, model: str, timeout: int = 180) -> None:
        super().__init__(model, timeout)
        self.base_url = base_url.rstrip("/")
        self.available = self.check_availability()
        self.models: List[str] = []

    def check_availability(self) -> bool:
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if r.status_code == 200:
                self.models = [m.get("name", "") for m in r.json().get("models", [])]
                return True
        except Exception as e:
            logger.warning("Ollama no disponible: %s", e)
        return False

    def _options(self, temperature: float, max_tokens: int, stream: bool) -> dict:
        return {
            "temperature": temperature,
            "num_predict": max_tokens,
            "top_p": 0.9,
            "repeat_penalty": 1.1,
            "stream": stream,
        }

    def generate(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.3, max_tokens: int = 2048) -> LLMResponse:
        if not self.available:
            return LLMResponse(False, error=f"Ollama no disponible en {self.base_url}")
        payload: Dict = {
            "model": self.model,
            "prompt": prompt,
            "options": self._options(temperature, max_tokens, stream=False),
        }
        if system_prompt:
            payload["system"] = system_prompt
        try:
            r = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=self.timeout)
            if r.status_code == 200:
                data = r.json()
                return LLMResponse(True, data.get("response", ""), model=self.model, meta={"eval_count": data.get("eval_count")})
            return LLMResponse(False, error=f"HTTP {r.status_code}: {r.text[:300]}")
        except requests.exceptions.Timeout:
            return LLMResponse(False, error="Tiempo de espera agotado (Ollama).")
        except Exception as e:
            return LLMResponse(False, error=str(e)[:300])

    def stream(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.3, max_tokens: int = 2048) -> Iterator[str]:
        if not self.available:
            yield ""
            return
        payload: Dict = {
            "model": self.model,
            "prompt": prompt,
            "options": self._options(temperature, max_tokens, stream=True),
        }
        if system_prompt:
            payload["system"] = system_prompt
        try:
            with requests.post(f"{self.base_url}/api/generate", json=payload, timeout=self.timeout, stream=True) as r:
                for line in r.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    try:
                        chunk = __import__("json").loads(line)
                        if chunk.get("response"):
                            yield chunk["response"]
                    except Exception:
                        continue
        except Exception as e:
            logger.error("Error en streaming Ollama: %s", e)
