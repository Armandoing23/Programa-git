from __future__ import annotations

import json
from typing import Dict, Iterator, List, Optional

import requests

from llm.base import BaseLLM, LLMResponse
from utils import logger


class OpenAICompatLLM(BaseLLM):
    def __init__(self, base_url: str, model: str, api_key: str = "not-needed", timeout: int = 180) -> None:
        super().__init__(model, timeout)
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.available = self.check_availability()
        self.models: List[str] = []

    def check_availability(self) -> bool:
        try:
            r = requests.get(f"{self.base_url}/models", headers=self._headers(), timeout=5)
            if r.status_code == 200:
                self.models = [m.get("id", "") for m in r.json().get("data", [])]
                return True
            return r.status_code == 200
        except Exception as e:
            logger.warning("Proveedor OpenAI-compat no disponible: %s", e)
        return False

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def generate(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.3, max_tokens: int = 2048) -> LLMResponse:
        if not self.available:
            return LLMResponse(False, error="Proveedor no disponible")
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        payload = {"model": self.model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens, "stream": False}
        try:
            r = requests.post(f"{self.base_url}/chat/completions", json=payload, headers=self._headers(), timeout=self.timeout)
            if r.status_code == 200:
                data = r.json()
                text = data["choices"][0]["message"]["content"]
                return LLMResponse(True, text, model=self.model)
            return LLMResponse(False, error=f"HTTP {r.status_code}: {r.text[:300]}")
        except Exception as e:
            return LLMResponse(False, error=str(e)[:300])

    def stream(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.3, max_tokens: int = 2048) -> Iterator[str]:
        if not self.available:
            yield ""
            return
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        payload = {"model": self.model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens, "stream": True}
        try:
            with requests.post(f"{self.base_url}/chat/completions", json=payload, headers=self._headers(), timeout=self.timeout, stream=True) as r:
                for line in r.iter_lines(decode_unicode=True):
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[len("data:"):].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk["choices"][0]["delta"].get("content")
                        if delta:
                            yield delta
                    except Exception:
                        continue
        except Exception as e:
            logger.error("Error en streaming OpenAI-compat: %s", e)
