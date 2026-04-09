"""
OpenAI-compatible provider — works with any endpoint that speaks the OpenAI chat API.

Used when LLM_PROVIDER=openai_compat. Covers:
  - OpenAI (GPT-4o, GPT-4.1, o3, ...)           LLM_BASE_URL=https://api.openai.com/v1
  - Google Gemini (via OpenAI compat layer)       LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
  - Moonshot / Kimi K2                            LLM_BASE_URL=https://api.moonshot.cn/v1
  - Zhipu / GLM                                   LLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4/
  - Ollama (local, no key needed)                 LLM_BASE_URL=http://localhost:11434/v1
  - LM Studio (local)                             LLM_BASE_URL=http://localhost:1234/v1
  - vLLM                                          LLM_BASE_URL=http://localhost:8000/v1
  - HuggingFace TGI (OpenAI-compat endpoints)    LLM_BASE_URL=https://api-inference.huggingface.co/v1

Required env vars:
  LLM_BASE_URL  — the full base URL (including /v1)
  LLM_MODEL     — model name as the provider expects (e.g. "llama3.2", "gpt-4o", "gemini-2.0-flash")
  LLM_API_KEY   — API key; use any non-empty string for local providers that don't check it
"""
from openai import OpenAI, APIError
from backend.config import LLM_MODEL, LLM_BASE_URL, LLM_API_KEY


class OpenAICompatProvider:
    def __init__(self) -> None:
        if not LLM_BASE_URL:
            raise ValueError(
                "LLM_BASE_URL must be set when LLM_PROVIDER=openai_compat. "
                "Example: LLM_BASE_URL=http://localhost:11434/v1"
            )
        self._client = OpenAI(
            api_key=LLM_API_KEY or "local",  # local providers require a non-empty string
            base_url=LLM_BASE_URL,
        )
        self.model = LLM_MODEL

    def complete(self, system: str, user: str, max_tokens: int) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            return (response.choices[0].message.content or "").strip()
        except APIError as e:
            raise RuntimeError(f"LLM API error ({self.model} @ {LLM_BASE_URL}): {e}") from e
