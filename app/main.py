from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events.

    Placeholder for future heavy warm-up work, e.g. loading a NetworkX graph
    into RAM.
    """
    app.state.sybil_graph = None
    yield


app = FastAPI(
    title="Web3 Sybil Detection Dashboard API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware (open for dashboard integration; tighten later as needed).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(api_router, prefix="/api/v1")

