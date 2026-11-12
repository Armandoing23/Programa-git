import requests
import json
import os
from typing import Optional, Dict, List

class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3"):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.available = self._check_availability()

    def _check_availability(self) -> bool:
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def get_available_models(self) -> List[str]:
        if not self.available:
            return []
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            if response.status_code == 200:
                data = response.json()
                return [m.get("name", "") for m in data.get("models", [])]
        except Exception:
            pass
        return []

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        stream: bool = False
    ) -> Dict:
        if not self.available:
            return {
                "success": False,
                "error": "Ollama service not available at " + self.base_url,
                "text": ""
            }

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "top_p": 0.9,
                "repeat_penalty": 1.1
            }
        }

        if system_prompt:
            payload["system"] = system_prompt

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=120,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "text": result.get("response", ""),
                    "model": self.model,
                    "total_duration": result.get("total_duration", 0),
                    "eval_count": result.get("eval_count", 0)
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text[:500]}",
                    "text": ""
                }
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "Request timed out (120s). Model may be too slow or prompt too long.",
                "text": ""
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)[:500],
                "text": ""
            }

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 2048,
        stream: bool = False
    ) -> Dict:
        if not self.available:
            return {
                "success": False,
                "error": "Ollama service not available",
                "text": ""
            }

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "top_p": 0.9,
                "repeat_penalty": 1.1
            }
        }

        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=120,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "text": result.get("message", {}).get("content", ""),
                    "model": self.model
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text[:500]}",
                    "text": ""
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)[:500],
                "text": ""
            }
