"""Shared LLM client utilities for the Agent1 pipeline.

Provides a centralized factory for creating Anthropic clients with
consistent SSL handling for corporate proxy environments.
"""
from __future__ import annotations

import os
from functools import lru_cache

import httpx
from anthropic import Anthropic

import structlog

logger = structlog.get_logger(__name__)


def get_anthropic_client() -> Anthropic:
    """Create an Anthropic client with appropriate SSL settings.
    
    SSL verification is disabled by default for corporate proxy environments.
    Set ANTHROPIC_VERIFY_SSL=true to enable verification.
    
    Returns:
        Configured Anthropic client instance.
    """
    verify_ssl = os.getenv("ANTHROPIC_VERIFY_SSL", "false").lower() == "true"
    
    if not verify_ssl:
        http_client = httpx.Client(verify=False)
        return Anthropic(http_client=http_client)
    
    return Anthropic()


def call_anthropic(
    prompt: str,
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 4096,
    temperature: float = 0.0,
    system: str | None = None,
) -> tuple[str, int, int]:
    """Make a call to the Anthropic API with standard error handling.
    
    Args:
        prompt: The user message content.
        model: Model name to use.
        max_tokens: Maximum tokens in response.
        temperature: Sampling temperature.
        system: Optional system prompt.
        
    Returns:
        Tuple of (response_text, input_tokens, output_tokens).
    """
    client = get_anthropic_client()
    
    messages = [{"role": "user", "content": prompt}]
    
    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": messages,
    }
    
    if system:
        kwargs["system"] = system
    
    response = client.messages.create(**kwargs)
    
    content = response.content[0].text if response.content else ""
    input_tokens = response.usage.input_tokens if response.usage else 0
    output_tokens = response.usage.output_tokens if response.usage else 0
    
    return content, input_tokens, output_tokens
