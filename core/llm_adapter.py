# core/llm_adapter.py — BYO-LLM Adapter (OpenAI-compatible, Ollama, vLLM, Anthropic, Google)
# Open-source core module (Apache-2.0). Secrets remain local.

import json
import os
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional


class LLMConfig:
    def __init__(
        self,
        provider: str = "openai_compatible",
        base_url: str = "http://localhost:11434/v1",
        api_key_env: str = "SKELION_LLM_KEY",
        analysis_model: str = "llama3:latest",
        fix_model: str = "llama3:latest",
        timeout_s: int = 60,
        max_input_tokens: int = 24000,
        max_output_tokens: int = 4000,
    ):
        self.provider = provider
        self.base_url = base_url.rstrip("/")
        self.api_key_env = api_key_env
        self.analysis_model = analysis_model
        self.fix_model = fix_model
        self.timeout_s = timeout_s
        self.max_input_tokens = max_input_tokens
        self.max_output_tokens = max_output_tokens

    @property
    def api_key(self) -> str:
        """Resolve API key strictly from local environment or secret file.
        Never stored in databases, never transmitted to Skelion cloud.
        """
        return os.getenv(
            self.api_key_env, os.getenv("OPENAI_API_KEY", "dummy-local-key")
        )


class LLMAdapter:
    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()

    def generate_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Send chat completion request to the configured local or remote provider."""
        target_model = model or self.config.fix_model
        url = f"{self.config.base_url}/chat/completions"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
        }

        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": self.config.max_output_tokens,
        }

        if tools:
            payload["tools"] = tools

        body_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=body_bytes, headers=headers)

        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout_s) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                choice = data.get("choices", [{}])[0]
                message = choice.get("message", {})
                return {
                    "status": "success",
                    "model": target_model,
                    "content": message.get("content", ""),
                    "tool_calls": message.get("tool_calls", []),
                    "usage": data.get("usage", {}),
                }
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            return {
                "status": "error",
                "status_code": e.code,
                "error": f"LLM HTTP {e.code}: {err_body}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"LLM connection failure to {url}: {str(e)}",
            }
