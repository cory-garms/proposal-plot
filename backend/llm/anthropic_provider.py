"""
Anthropic provider — wraps the official anthropic SDK.

Used when LLM_PROVIDER=anthropic (default).
Requires ANTHROPIC_API_KEY in the environment.
"""
import anthropic
from backend.config import ANTHROPIC_API_KEY, LLM_MODEL


class AnthropicProvider:
    def __init__(self) -> None:
        self._client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.model = LLM_MODEL

    def complete(self, system: str, user: str, max_tokens: int) -> str:
        try:
            response = self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return response.content[0].text.strip()
        except anthropic.APIError as e:
            raise RuntimeError(f"Anthropic API error: {e}") from e
