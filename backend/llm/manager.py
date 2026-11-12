from __future__ import annotations

from typing import Optional

from config import Config, get_config
from llm.base import BaseLLM
from llm.ollama import OllamaLLM
from llm.openai_compat import OpenAICompatLLM


class LLMManager:
    def __init__(self, config: Optional[Config] = None) -> None:
        self.config = config or get_config()
        self.primary = self._build(self.config.provider, self.config.default_model)
        self.fallbacks: list[BaseLLM] = []
        for m in self.config.fallback_models:
            self.fallbacks.append(self._build(self.config.provider, m))

    def _build(self, provider: str, model: str) -> BaseLLM:
        if provider == "ollama":
            return OllamaLLM(self.config.ollama_url, model, self.config.request_timeout)
        return OpenAICompatLLM(self.config.openai_base_url, model, self.config.openai_api_key, self.config.request_timeout)

    @property
    def available(self) -> bool:
        return self.primary.available

    def list_models(self) -> list[str]:
        models = list(self.primary.models) if hasattr(self.primary, "models") else []
        return models or [self.primary.model]

    def generate(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.3, max_tokens: int = 2048):
        resp = self.primary.generate(prompt, system_prompt, temperature, max_tokens)
        if resp.success or not self.fallbacks:
            return resp
        for fb in self.fallbacks:
            r = fb.generate(prompt, system_prompt, temperature, max_tokens)
            if r.success:
                return r
        return resp

    def stream(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.3, max_tokens: int = 2048):
        return self.primary.stream(prompt, system_prompt, temperature, max_tokens)
