from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from backend.database import init_db
from backend.routers.solicitations import router as solicitations_router
from backend.routers.capabilities import router as capabilities_router
from backend.routers.projects import router as projects_router
from backend.routers.dashboard import router as dashboard_router
from backend.routers.keywords import router as keywords_router
from backend.routers.auth import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="ProposalPilot API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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


@app.get("/health")
def health():
    return {"status": "ok"}
