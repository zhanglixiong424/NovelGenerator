"""
AI Service Layer — Provider abstraction with fallback & retry.

All providers use the OpenAI-compatible /chat/completions endpoint (streaming).
"""

import asyncio
import json
import logging
import time
from typing import AsyncGenerator

import httpx

from app.encryption import decrypt_api_key
from app.models import AIProviderConfig

log = logging.getLogger(__name__)

MAX_RETRIES = 3
MAX_BACKOFF = 30


class AIServiceError(Exception):
    pass


class AllProvidersFailedError(AIServiceError):
    pass


async def _stream_chat(
    api_key: str,
    base_url: str,
    model: str,
    messages: list[dict],
    max_tokens: int = 4096,
    temperature: float = 0.7,
    timeout: float = 120.0,
) -> AsyncGenerator[str, None]:
    """Stream chat completions from an OpenAI-compatible endpoint."""
    url = base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": True,
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=10.0)) as client:
        async with client.stream("POST", url, headers=headers, json=body) as resp:
            if resp.status_code != 200:
                text = ""
                async for chunk in resp.aiter_text():
                    text += chunk
                    if len(text) > 500:
                        break
                raise AIServiceError(f"HTTP {resp.status_code}: {text[:500]}")

            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[6:]
                if data.strip() == "[DONE]":
                    break
                try:
                    obj = json.loads(data)
                    delta = obj.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
                except (json.JSONDecodeError, IndexError, KeyError):
                    continue


async def _non_stream_chat(
    api_key: str,
    base_url: str,
    model: str,
    messages: list[dict],
    max_tokens: int = 4096,
    temperature: float = 0.7,
    timeout: float = 120.0,
) -> str:
    """Non-streaming chat completion. Returns full response text."""
    url = base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=10.0)) as client:
        resp = await client.post(url, headers=headers, json=body)
        if resp.status_code != 200:
            raise AIServiceError(f"HTTP {resp.status_code}: {resp.text[:500]}")
        data = resp.json()
        return data["choices"][0]["message"]["content"]


class AIService:
    """Manages AI generation with provider priority + fallback + retry."""

    def __init__(self, providers: list[AIProviderConfig]):
        """providers should be pre-sorted by priority (ascending)."""
        self.providers = [p for p in providers if p.is_enabled]

    async def generate_stream(
        self,
        messages: list[dict],
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        """Stream generation with fallback across providers."""
        if not self.providers:
            raise AllProvidersFailedError("没有可用的 AI 提供商，请先配置")

        errors: list[str] = []

        for provider in self.providers:
            api_key = decrypt_api_key(provider.api_key_encrypted)
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    collected = []
                    async for chunk in _stream_chat(
                        api_key=api_key,
                        base_url=provider.base_url,
                        model=provider.model_name,
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=temperature,
                    ):
                        collected.append(chunk)
                        yield chunk

                    # If we got here, generation succeeded
                    if collected:
                        return
                    # Empty response — treat as failure
                    raise AIServiceError("AI 返回空响应")

                except Exception as e:
                    wait = min(2 ** attempt, MAX_BACKOFF)
                    msg = f"{provider.name} attempt {attempt}/{MAX_RETRIES} failed: {e}"
                    log.warning(msg)
                    errors.append(msg)
                    if attempt < MAX_RETRIES:
                        await asyncio.sleep(wait)

            log.error(f"{provider.name} exhausted retries, trying next provider")

        raise AllProvidersFailedError(
            f"所有 AI 提供商均不可用:\n" + "\n".join(errors[-6:])
        )

    async def generate_full(
        self,
        messages: list[dict],
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        """Non-streaming generation with fallback. Returns full text."""
        if not self.providers:
            raise AllProvidersFailedError("没有可用的 AI 提供商，请先配置")

        errors: list[str] = []

        for provider in self.providers:
            api_key = decrypt_api_key(provider.api_key_encrypted)
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    result = await _non_stream_chat(
                        api_key=api_key,
                        base_url=provider.base_url,
                        model=provider.model_name,
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=temperature,
                    )
                    if result.strip():
                        return result
                    raise AIServiceError("AI 返回空响应")
                except Exception as e:
                    wait = min(2 ** attempt, MAX_BACKOFF)
                    msg = f"{provider.name} attempt {attempt}/{MAX_RETRIES} failed: {e}"
                    log.warning(msg)
                    errors.append(msg)
                    if attempt < MAX_RETRIES:
                        await asyncio.sleep(wait)

            log.error(f"{provider.name} exhausted retries, trying next provider")

        raise AllProvidersFailedError(
            f"所有 AI 提供商均不可用:\n" + "\n".join(errors[-6:])
        )
