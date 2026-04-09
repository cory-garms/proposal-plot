import os
from dotenv import load_dotenv

load_dotenv()

# --- Database & server ---
DB_PATH = os.getenv("DB_PATH", "proposalpilot.db")
BACKEND_HOST = os.getenv("BACKEND_HOST", "0.0.0.0")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))

# --- Auth ---
JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 72
# Set ALLOW_REGISTRATION=false in .env to lock signups after initial user creation
ALLOW_REGISTRATION = os.getenv("ALLOW_REGISTRATION", "true").lower() != "false"

# --- Scheduler ---
SCHEDULER_ENABLED = os.getenv("SCHEDULER_ENABLED", "true").lower() != "false"
SCHEDULER_HOUR = int(os.getenv("SCHEDULER_HOUR", "2"))
SCHEDULER_MINUTE = int(os.getenv("SCHEDULER_MINUTE", "0"))

# --- LLM provider ---
# LLM_PROVIDER: "anthropic" (default) or "openai_compat"
#
# openai_compat covers: OpenAI, Google Gemini, Moonshot/Kimi K2, Zhipu/GLM,
# Ollama, LM Studio, vLLM, HuggingFace TGI — any endpoint speaking the
# OpenAI chat completions API.
#
# Examples:
#   LLM_PROVIDER=anthropic    LLM_MODEL=claude-sonnet-4-6  (uses ANTHROPIC_API_KEY)
#   LLM_PROVIDER=openai_compat LLM_MODEL=gpt-4o            LLM_BASE_URL=https://api.openai.com/v1
#   LLM_PROVIDER=openai_compat LLM_MODEL=gemini-2.0-flash  LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
#   LLM_PROVIDER=openai_compat LLM_MODEL=kimi-k2           LLM_BASE_URL=https://api.moonshot.cn/v1
#   LLM_PROVIDER=openai_compat LLM_MODEL=glm-4             LLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4/
#   LLM_PROVIDER=openai_compat LLM_MODEL=llama3.2          LLM_BASE_URL=http://localhost:11434/v1
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic")
LLM_MODEL = os.getenv("LLM_MODEL", "claude-sonnet-4-6")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")   # required for openai_compat
LLM_API_KEY = os.getenv("LLM_API_KEY", "")     # required for commercial openai_compat providers

# --- Anthropic (used when LLM_PROVIDER=anthropic) ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# --- CORS ---
# Comma-separated list of allowed origins.
# In production set this to your GitHub Pages URL, e.g.:
#   CORS_ORIGINS=https://cory-garms.github.io
# Defaults to * (open) for local development only.
_cors_env = os.getenv("CORS_ORIGINS", "*")
CORS_ORIGINS: list[str] = [o.strip() for o in _cors_env.split(",") if o.strip()]
