import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from backend.config import JWT_SECRET, LLM_PROVIDER, LLM_MODEL, LLM_BASE_URL, ANTHROPIC_API_KEY, SCHEDULER_ENABLED, SCHEDULER_HOUR, SCHEDULER_MINUTE, CORS_ORIGINS
from backend.scheduler import start_scheduler, stop_scheduler, get_scheduler_info
from backend.database import init_db
from backend.routers.solicitations import router as solicitations_router
from backend.routers.capabilities import router as capabilities_router
from backend.routers.projects import router as projects_router
from backend.routers.dashboard import router as dashboard_router
from backend.routers.keywords import router as keywords_router
from backend.routers.auth import router as auth_router
from backend.routers.generate_capabilities import router as gen_capabilities_router

_WARNINGS: list[str] = []


def _validate_config() -> None:
    """Log warnings for misconfigured or insecure settings at startup."""
    if JWT_SECRET == "change-me-in-production":
        msg = (
            "WARNING: JWT_SECRET is set to the default insecure value. "
            "Tokens can be forged. Set a real secret in .env:\n"
            "  JWT_SECRET=$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
        )
        _WARNINGS.append(msg)
        print(f"\n{'='*60}\n{msg}\n{'='*60}\n", file=sys.stderr)

    if LLM_PROVIDER == "anthropic" and not ANTHROPIC_API_KEY:
        msg = "WARNING: LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set. Draft generation will fail."
        _WARNINGS.append(msg)
        print(msg, file=sys.stderr)

    if LLM_PROVIDER == "openai_compat" and not LLM_BASE_URL:
        msg = "WARNING: LLM_PROVIDER=openai_compat but LLM_BASE_URL is not set. Draft generation will fail."
        _WARNINGS.append(msg)
        print(msg, file=sys.stderr)

    print(f"[startup] LLM provider: {LLM_PROVIDER} | model: {LLM_MODEL}", file=sys.stderr)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _validate_config()
    init_db()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="ProposalPilot API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(solicitations_router)
app.include_router(capabilities_router)
app.include_router(projects_router)
app.include_router(dashboard_router)
app.include_router(keywords_router)
app.include_router(auth_router)
app.include_router(gen_capabilities_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/config")
def client_config():
    """
    Runtime configuration for the frontend.
    Returns the LLM provider info so the UI can display which model is active.
    Never returns secrets.
    """
    return {
        "llm_provider": LLM_PROVIDER,
        "llm_model": LLM_MODEL,
        "warnings": _WARNINGS,
        "scheduler": get_scheduler_info(),
    }
