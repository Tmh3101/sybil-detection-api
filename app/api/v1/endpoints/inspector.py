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

router = APIRouter()

@router.get("/profile/{profile_id}", response_model=InspectorProfileResponse)
async def get_profile_details(profile_id: str, request: Request):
    """
    Get profile details and its ego-graph (radius=1).
    Checks RAM cache first, falls back to BigQuery if missing.
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
        # undirected=False to keep original directed interaction edges
        subgraph = nx.ego_graph(G, profile_id, radius=1, undirected=False)
        
        # 1. Profile Info
        node_data = G.nodes[profile_id]
        profile_info = ProfileInfo(
            id=profile_id,
            handle=node_data.get("handle", "unknown"),
            picture_url=node_data.get("picture_url", ""),
            owned_by=node_data.get("owned_by", "")
        )
        
        # 2. Analysis (Placeholder for AI Inference Phase)
        analysis = AnalysisInfo()
        
        # 3. Local Graph
        nodes = []
        for n_id, attrs in subgraph.nodes(data=True):
            nodes.append(LocalGraphNode(
                id=n_id,
                attributes={
                    "handle": attrs.get("handle", "unknown"),
                    "picture_url": attrs.get("picture_url", ""),
                    "owned_by": attrs.get("owned_by", "")
                }
            ))
            
        links = []
        for u, v, data in subgraph.edges(data=True):
            if data == {}:
                continue;
        
            links.append(LocalGraphLink(
                source=u,
                target=v,
                edge_type=data.get("type", "MENTION"),
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
