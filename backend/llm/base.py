from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Iterator, List, Optional


class LLMResponse:
    def __init__(self, success: bool, text: str = "", error: Optional[str] = None, model: str = "", meta: Optional[dict] = None) -> None:
        self.success = success
        self.text = text
        self.error = error
        self.model = model
        self.meta = meta or {}


class BaseLLM(ABC):
    def __init__(self, model: str, timeout: int = 180) -> None:
        self.model = model
        self.timeout = timeout
        self.available = False

    @abstractmethod
    def check_availability(self) -> bool:
        ...

    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.3, max_tokens: int = 2048) -> LLMResponse:
        ...

    @abstractmethod
    def stream(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.3, max_tokens: int = 2048) -> Iterator[str]:
        ...

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.3, max_tokens: int = 2048) -> LLMResponse:
        raise NotImplementedError
