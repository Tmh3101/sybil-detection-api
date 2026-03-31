import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.services.inspector_service import load_reference_graph
from app.core.model_loader import load_models
from app.core.config import get_settings

settings = get_settings()

logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events.

    Initializes the Graph Backbone and AI Models.
    """
    logger.info("Initializing Graph Backbone...")

    app.state.graph = await load_reference_graph(
        settings.GRAPH_DATA_PATH, settings.NODE_METADATA_PATH
    )

    logger.info(
        f"Backbone ready! Nodes: {app.state.graph.number_of_nodes()}, "
        f"Edges: {app.state.graph.number_of_edges()}"
    )

    logger.info("Loading AI Models...")
    app.state.models = load_models("data")
    logger.info("AI Models loaded.")

    yield

    # Shutdown logic
    app.state.graph.clear()
    app.state.models.clear()
    logger.info("Resources cleared.")


app = FastAPI(
    title="Lens Protocol Sybil Detection API",
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
app.include_router(api_router, prefix=settings.API_V1_STR)
