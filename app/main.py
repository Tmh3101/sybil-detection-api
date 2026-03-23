import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.services.inspector_service import load_reference_graph

logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events.

    Initializes the Graph Backbone by loading the reference graph into RAM.
    """
    logger.info("Initializing Graph Backbone...")
    
    # Paths for data files (hardcoded for now, move to config later)
    pt_path = "data/graph.pt"
    meta_path = "data/nodes_full.csv"

    app.state.graph = await load_reference_graph(pt_path, meta_path)
    
    logger.info(
        f"Backbone ready! Nodes: {app.state.graph.number_of_nodes()}, "
        f"Edges: {app.state.graph.number_of_edges()}"
    )
    
    yield
    
    # Shutdown logic
    app.state.graph.clear()
    logger.info("Graph Backbone cleared.")


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

