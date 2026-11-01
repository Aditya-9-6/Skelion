import os
import asyncio
import logging
from typing import AsyncGenerator, Optional

from anthropic import AsyncAnthropic
from gossipmesh.providers.base import BaseProvider
from gossipmesh.providers.models import (
    GenerationRequest,
    GenerationResponse,
    ProviderHealth,
    Usage,
)

logger = logging.getLogger(__name__)
rate_limits_saved_total = None


class AnthropicAdapter(BaseProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self.client = AsyncAnthropic(api_key=self.api_key)

    async def generate(
        self,
        request: GenerationRequest,
        max_retries: int = 3,
        initial_backoff: float = 1.0,
    ) -> GenerationResponse:
        backoff = initial_backoff
        max_backoff = 30.0
        for attempt in range(max_retries):
            try:
                system_prompt = next(
                    (msg.content for msg in request.messages if msg.role == "system"),
                    "",
                )
                user_messages = [
                    {"role": msg.role, "content": msg.content}
                    for msg in request.messages
                    if msg.role != "system"
                ]
                response = await self.client.messages.create(
                    model=request.model,
                    max_tokens=request.max_tokens or 1024,
                    system=system_prompt if system_prompt else None,
                    messages=user_messages,
                )
                content = response.content[0].text if response.content else ""
                return GenerationResponse(
                    content=content,
                    model=request.model,
                    provider="anthropic",
                    usage=Usage(
                        prompt_tokens=response.usage.input_tokens,
                        completion_tokens=response.usage.output_tokens,
                        total_tokens=response.usage.input_tokens
                        + response.usage.output_tokens,
                    ),
                )
            except Exception as e:
                if getattr(e, "status_code", None) == 429:
                    if rate_limits_saved_total is not None:
                        rate_limits_saved_total.inc()
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, max_backoff)
                else:
                    raise
        raise RuntimeError("Max retries exceeded for Anthropic provider")

    async def generate_stream(
        self, request: GenerationRequest
    ) -> AsyncGenerator[str, None]:
        system_prompt = next(
            (msg.content for msg in request.messages if msg.role == "system"), ""
        )
        user_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in request.messages
            if msg.role != "system"
        ]
        async with self.client.messages.stream(
            model=request.model,
            max_tokens=request.max_tokens or 1024,
            system=system_prompt if system_prompt else None,
            messages=user_messages,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def check_health(self) -> ProviderHealth:
        return ProviderHealth(is_healthy=True, latency_ms=10.0)
