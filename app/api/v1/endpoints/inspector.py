import networkx as nx
from fastapi import APIRouter, Request, HTTPException, status
from typing import Any

from app.schemas.inspector import (
    InspectorProfileResponse,
    ProfileInfo,
    AnalysisInfo,
    LocalGraph,
    LocalGraphNode,
    LocalGraphLink,
)

from app.services.fallback_service import fetch_and_embed_node
from app.services.inference_service import evaluate_subgraph

router = APIRouter()

@router.get("/profile/{profile_id}", response_model=InspectorProfileResponse)
async def get_profile_details(profile_id: str, request: Request):
    """
    Get profile details and its ego-graph (radius=1).
    Checks RAM cache first, falls back to BigQuery if missing.
    Executes Hybrid AI inference to detect Sybil patterns.
    """
    # Check if the graph backbone is initialized
    if not hasattr(request.app.state, "graph") or request.app.state.graph is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Graph Backbone is not initialized yet. Please try again later."
        )
    
    G = request.app.state.graph
    
    # Traffic Controller: Cache Hit vs Cache Miss
    if profile_id not in G:
        # Cache Miss -> Trigger Fallback Pipeline
        success = await fetch_and_embed_node(request.app, profile_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found on Lens Protocol or Backbone."
            )
    
    try:
        # At this point, profile_id is guaranteed to be in G
        # Extract Ego-graph (radius=1)
        subgraph = nx.ego_graph(G, profile_id, radius=1, undirected=False)
        
        # 1. Profile Info
        node_data = G.nodes[profile_id]
        profile_info = ProfileInfo(
            id=profile_id,
            handle=node_data.get("handle", "unknown"),
            picture_url=node_data.get("picture_url", ""),
            owned_by=node_data.get("owned_by", "")
        )
        
        # 2. AI Inference Analysis
        models = getattr(request.app.state, "models", {})
        inference_result = await evaluate_subgraph(models, subgraph, profile_id)
        
        if inference_result:
            analysis = AnalysisInfo(
                sybil_probability=inference_result["risk_score"],
                classification=inference_result["label"],
                reasoning=[inference_result["reasoning"]]
            )
        else:
            analysis = AnalysisInfo(
                classification="INFERENCE_FAILED",
                reasoning=["The AI models failed to process this subgraph or are not available."]
            )
        
        # 3. Local Graph
        nodes = []
        for n_id, attrs in subgraph.nodes(data=True):
            nodes.append(LocalGraphNode(
                id=n_id,
                attributes={
                    "handle": attrs.get("handle", "unknown"),
                    "picture_url": attrs.get("picture_url", ""),
                    "owned_by": attrs.get("owned_by", ""),
                    "created_on": attrs.get("created_on", ""),
                    "trust_score": attrs.get("trust_score", 0.0)
                }
            ))
            
        links = []
        for u, v, data in subgraph.edges(data=True):
            links.append(LocalGraphLink(
                source=u,
                target=v,
                edge_type=data.get("type", "INTERACT"),
                weight=data.get("weight", 1.0)
            ))
            
        return InspectorProfileResponse(
            profile_info=profile_info,
            analysis=analysis,
            local_graph=LocalGraph(nodes=nodes, links=links)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while extracting ego-graph: {str(e)}"
        )
