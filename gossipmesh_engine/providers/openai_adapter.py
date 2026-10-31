from typing import Any
from typing import AsyncGenerator
import os
import asyncio
import time
from prometheus_client import Counter

rate_limits_saved_total = Counter(
    "rate_limits_saved_total", "Number of 429 rate limit events"
)
from gossipmesh_agent.key_pool import KeyPool

# Initialize global key pool from environment variable (comma‑separated list of keys)
_key_pool = KeyPool([k for k in os.getenv("OPENAI_API_KEYS", "").split(",") if k])


# Helper to obtain a client with the current key
def _client_for_key(key: str):
    return AsyncOpenAI(api_key=key)


from openai import AsyncOpenAI
import tiktoken

from gossipmesh.providers.base import BaseProvider
from gossipmesh.providers.models import (
    GenerationRequest,
    GenerationResponse,
    ProviderHealth,
    Usage,
)


class OpenAIProvider(BaseProvider):
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.client = AsyncOpenAI(api_key=self.api_key)

    @property
    def provider_name(self) -> str:
        return "openai"

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        # Attempt LLM request with key rotation and 429 handling
        backoff = 1
        max_backoff = 60
        while True:
            key = _key_pool.get_key()
            client = _client_for_key(key)
            formatted_messages = [
                {"role": msg.role, "content": msg.content} for msg in request.messages
            ]
            try:
                response = await client.chat.completions.create(
                    model=request.model,
                    messages=formatted_messages,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                    stop=request.stop_sequences,
                    timeout=request.timeout,
                )
                break
            except Exception as e:
                # Handle rate limit (HTTP 429)
                if getattr(e, "status_code", None) == 429:
                    rate_limits_saved_total.inc()
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, max_backoff)
                    continue
                raise

        usage = Usage(
            prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
            completion_tokens=response.usage.completion_tokens if response.usage else 0,
            total_tokens=response.usage.total_tokens if response.usage else 0,
            cost_estimate_usd=0.0,  # To be implemented properly via a pricing table
        )

        return GenerationResponse(
            content=response.choices[0].message.content or "",
            model=response.model,
            usage=usage,
            raw_response=response.model_dump(),
        )

    async def generate_stream(
        self, request: GenerationRequest
    ) -> AsyncGenerator[str, None]:  # type: ignore
        formatted_messages: list[Any] = [
            {"role": msg.role, "content": msg.content} for msg in request.messages
        ]
        stream: Any = await self.client.chat.completions.create(
            model=request.model,
            messages=formatted_messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stop=request.stop_sequences,
            stream=True,
            timeout=request.timeout,
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def check_health(self) -> ProviderHealth:
        start_time = time.time()
        try:
            # simple models query to check auth and network
            await self.client.models.list()
            latency = (time.time() - start_time) * 1000
            return ProviderHealth(is_healthy=True, latency_ms=latency)
        except Exception as e:
            return ProviderHealth(is_healthy=False, error=str(e))

    def count_tokens(self, text: str) -> int:
        # Defaulting to cl100k_base which is used by most modern OpenAI models (GPT-4, 3.5-turbo)
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
