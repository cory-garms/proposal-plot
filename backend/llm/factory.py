"""
LLM client factory.

Returns a singleton LLMClient based on LLM_PROVIDER in the environment.
Call get_llm_client() anywhere; the same instance is reused across calls.

To switch providers at runtime (e.g. in tests), call reset_llm_client() first.
"""
from functools import lru_cache
from backend.config import LLM_PROVIDER
from backend.llm.base import LLMClient


@lru_cache(maxsize=1)
def get_llm_client() -> LLMClient:
    """Return the configured LLM client (cached singleton)."""
    if LLM_PROVIDER == "openai_compat":
        from backend.llm.openai_compat_provider import OpenAICompatProvider
        return OpenAICompatProvider()
    elif LLM_PROVIDER == "anthropic":
        from backend.llm.anthropic_provider import AnthropicProvider
        return AnthropicProvider()
    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER '{LLM_PROVIDER}'. "
            "Valid values: anthropic, openai_compat"
        )


def reset_llm_client() -> None:
    """Clear the cached client. Useful when env vars change between tests."""
    get_llm_client.cache_clear()
