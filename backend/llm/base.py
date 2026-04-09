"""
LLM client interface.

All providers must implement complete(system, user, max_tokens) -> str.
The model property returns the identifier written to the drafts table.
"""
from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMClient(Protocol):
    model: str

    def complete(self, system: str, user: str, max_tokens: int) -> str:
        """
        Send a single-turn prompt and return the text response.
        Raises RuntimeError on API / network failure.
        """
        ...
