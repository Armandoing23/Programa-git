from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

Provider = Literal["ollama", "openai_compat"]

BASE_DIR = Path(__file__).resolve().parent


def _load_env() -> None:
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


class Config:
    def __init__(self) -> None:
        _load_env()
        self.knowledge_dir = Path(
            os.environ.get("KNOWLEDGE_DIR", str(BASE_DIR / "knowledge"))
        )
        self.data_dir = Path(os.environ.get("DATA_DIR", str(BASE_DIR / "data")))
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.provider: Provider = os.environ.get("LLM_PROVIDER", "ollama")  # type: ignore
        self.ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
        self.openai_base_url = os.environ.get("OPENAI_BASE_URL", "http://localhost:1234/v1")
        self.openai_api_key = os.environ.get("OPENAI_API_KEY", "not-needed")

        self.default_model = os.environ.get("LLM_MODEL", "llama3")
        self.fallback_models = [
            m.strip() for m in os.environ.get("LLM_FALLBACK_MODELS", "").split(",") if m.strip()
        ]
        self.temperature = float(os.environ.get("LLM_TEMPERATURE", "0.3"))
        self.max_tokens = int(os.environ.get("LLM_MAX_TOKENS", "3000"))
        self.request_timeout = int(os.environ.get("LLM_TIMEOUT", "180"))

        self.host = os.environ.get("HOST", "0.0.0.0")
        self.port = int(os.environ.get("PORT", "8000"))

        self.log_level = os.environ.get("LOG_LEVEL", "INFO")
        self.enable_memory = os.environ.get("ENABLE_MEMORY", "true").lower() in ("1", "true", "yes")
        self.memory_path = self.data_dir / "memory.json"
        self.feedback_path = self.data_dir / "feedback.jsonl"


@lru_cache(maxsize=1)
def get_config() -> Config:
    return Config()
