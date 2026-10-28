import os
import asyncio
from prometheus_client import Counter
from gossipmesh_agent.key_pool import KeyPool

# Initialize global key pool for Anthropic API keys (reuse OPENAI_API_KEYS env var for simplicity)
_key_pool = KeyPool([k for k in os.getenv("OPENAI_API_KEYS", "").split(",") if k])
_key_pool = KeyPool([k for k in os.getenv("OPENAI_API_KEYS", "").split(",") if k])

import time
from anthropic import AsyncAnthropic

from gossipmesh.providers.base import BaseProvider
from gossipmesh.providers.models import GenerationRequest, GenerationResponse, ProviderHealth, Usage


class AnthropicProvider(BaseProvider):
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.client = AsyncAnthropic(api_key=self.api_key)

    @property
    def provider_name(self) -> str:
        return "anthropic"

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        # Attempt LLM request with key rotation and 429 handling
        backoff = 1
        max_backoff = 60
        while True:
            key = _key_pool.get_key()
            client = AsyncAnthropic(api_key=key)
            system_prompt = next((msg.content for msg in request.messages if msg.role == "system"), "")
            messages = [{"role": msg.role, "content": msg.content} for msg in request.messages if msg.role != "system"]
            try:
                response = await client.messages.create(
                    model=request.model,
                    system=system_prompt,
                    messages=messages,  # type: ignore
                    max_tokens=request.max_tokens,
                    temperature=request.temperature,
                    stop_sequences=request.stop_sequences or [],
                    timeout=request.timeout,
                )
                break
            except Exception as e:
                if getattr(e, "status_code", None) == 429:
                    rate_limits_saved_total.inc()
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, max_backoff)
                    continue
                raise

        time.time()

        usage = Usage(
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
            total_tokens=response.usage.input_tokens + response.usage.output_tokens,
            cost_estimate_usd=0.0,
        )

        content = ""
        if response.content:
            content = response.content[0].text  # type: ignore

        return GenerationResponse(
            content=content, model=request.model, usage=usage, raw_response={"id": response.id, "type": response.type}
        )

    async def generate_stream(self, request: GenerationRequest) -> AsyncGenerator[str, None]:  # type: ignore
        system_prompt = next((msg.content for msg in request.messages if msg.role == "system"), "")
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages if msg.role != "system"]

        async with self.client.messages.stream(
            model=request.model,
            system=system_prompt,
            messages=messages,  # type: ignore
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            stop_sequences=request.stop_sequences or [],
            timeout=request.timeout,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def check_health(self) -> ProviderHealth:
        start_time = time.time()
        try:
            # simple ping query
            await self.client.messages.create(
                model="claude-3-haiku-20240307", max_tokens=1, messages=[{"role": "user", "content": "hello"}]
            )
            latency = (time.time() - start_time) * 1000
            return ProviderHealth(is_healthy=True, latency_ms=latency)
        except Exception as e:
            return ProviderHealth(is_healthy=False, error=str(e))

    def count_tokens(self, text: str) -> int:
        # Client side token counting for Anthropic is typically done via their API,
        # but for local approximation we can use an average word-to-token ratio
        return int(len(text.split()) * 1.3)
