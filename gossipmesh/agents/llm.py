from typing import AsyncGenerator, List, Optional, Any
import os
import asyncio
import time
import logging

from gossipmesh_engine.providers.models import GenerationRequest, GenerationResponse, ProviderHealth, Usage

logger = logging.getLogger(__name__)

try:
    from llama_cpp import Llama
except ImportError:
    Llama = None


class LocalLlamaFallbackProvider:
    """
    Local Llama.cpp fallback provider for sovereign, offline, or rate-limit-resilient agent completions.
    """
    def __init__(self, model_path: Optional[str] = None, n_ctx: int = 2048, n_threads: Optional[int] = None):
        self.model_path = model_path or os.getenv("LLAMA_CPP_MODEL_PATH", "models/llama-model.gguf")
        self.n_ctx = n_ctx
        self.n_threads = n_threads or os.cpu_count() or 4
        self._model: Optional[Any] = None

    @property
    def provider_name(self) -> str:
        return "llama_cpp_local"

    def _load_model(self) -> Any:
        if Llama is None:
            raise RuntimeError("llama-cpp-python package is not installed.")
        if self._model is None:
            if not os.path.exists(self.model_path):
                raise FileNotFoundError(f"Llama model file not found at {self.model_path}")
            logger.info(f"Loading local Llama.cpp model from {self.model_path} with {self.n_threads} threads...")
            self._model = Llama(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_threads=self.n_threads,
                verbose=False
            )
        return self._model

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        def _sync_generate():
            model = self._load_model()
            messages = [{"role": m.role, "content": m.content} for m in request.messages]
            
            # Convert stop sequences if needed
            stop = request.stop_sequences if request.stop_sequences else []
            
            completion = model.create_chat_completion(
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stop=stop
            )
            return completion

        start_time = time.time()
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, _sync_generate)
        
        choice = response["choices"][0]
        content = choice["message"]["content"]
        usage_data = response.get("usage", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
        
        usage = Usage(
            prompt_tokens=usage_data.get("prompt_tokens", 0),
            completion_tokens=usage_data.get("completion_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0),
            cost_estimate_usd=0.0
        )

        return GenerationResponse(
            content=content,
            model=request.model,
            usage=usage,
            raw_response=response
        )

    async def generate_stream(self, request: GenerationRequest) -> AsyncGenerator[str, None]:
        def _sync_stream():
            model = self._load_model()
            messages = [{"role": m.role, "content": m.content} for m in request.messages]
            stop = request.stop_sequences if request.stop_sequences else []
            return model.create_chat_completion(
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stop=stop,
                stream=True
            )

        loop = asyncio.get_running_loop()
        stream = await loop.run_in_executor(None, _sync_stream)

        for chunk in stream:
            choices = chunk.get("choices", [])
            if choices:
                delta = choices[0].get("delta", {})
                content = delta.get("content")
                if content:
                    yield content
                    
    async def check_health(self) -> ProviderHealth:
        start_time = time.time()
        try:
            if Llama is None:
                return ProviderHealth(is_healthy=False, error="llama-cpp-python not installed")
            if not os.path.exists(self.model_path):
                return ProviderHealth(is_healthy=False, error=f"Model path not found: {self.model_path}")
            latency = (time.time() - start_time) * 1000
            return ProviderHealth(is_healthy=True, latency_ms=latency)
        except Exception as e:
            return ProviderHealth(is_healthy=False, error=str(e))
