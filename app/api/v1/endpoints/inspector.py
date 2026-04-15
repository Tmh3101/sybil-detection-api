import pandas as pd
import networkx as nx
from fastapi import APIRouter, Request, HTTPException, status, Depends, Query
from sqlalchemy.orm import Session

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
from app.database import get_db, InspectorHistory

router = APIRouter()


@router.get("/profile/{profile_id}", response_model=InspectorProfileResponse)
async def get_profile_details(
    profile_id: str,
    request: Request,
    debug: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    """
    Get profile details and its ego-graph (radius=1).
    Checks RAM cache first, falls back to BigQuery if missing.
    Executes Hybrid AI inference to detect Sybil patterns.
    """
    # Check if the graph backbone is initialized
    if not hasattr(request.app.state, "graph") or request.app.state.graph is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Graph Backbone is not initialized yet. Please try again later.",
        )

    G = request.app.state.graph

    profile_id = profile_id.lower()

    # Traffic Controller: Cache Hit vs Cache Miss
    fallback_debug = None
    if profile_id not in G:
        # Cache Miss -> Trigger Fallback Pipeline
        success, fallback_debug = await fetch_and_embed_node(request.app, profile_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found on Lens Protocol or Backbone.",
            )
    try:
        # At this point, profile_id is guaranteed to be in G
        # Define a safe converter for string attributes (handle NaN from pandas)
        def safe_str(x, default=""):
            return str(x) if pd.notna(x) else default

        # Extract Ego-graph (radius=2)
        # Using undirected=True to capture both incoming (followers) and outgoing edges,
        # and to correctly retrieve undirected relations like SIMILARITY and CO-OWNER.
        subgraph = nx.ego_graph(G, profile_id, radius=2, undirected=True)

        # 1. Profile Info
        node_data = G.nodes[profile_id]
        profile_info = ProfileInfo(
            id=profile_id,
            handle=safe_str(node_data.get("handle"), "unknown"),
            picture_url=safe_str(node_data.get("picture_url"), ""),
            owned_by=safe_str(node_data.get("owned_by"), ""),
        )

        # 2. AI Inference Analysis
        models = getattr(request.app.state, "models", {})
        inference_result = await evaluate_subgraph(models, subgraph, profile_id)

        if inference_result:
            analysis = AnalysisInfo(
                predict_label=inference_result["predict_label"],
                predict_proba=inference_result["predict_proba"],
                reasoning=inference_result["reasoning"],
            )
        else:
            analysis = AnalysisInfo(
                predict_label="INFERENCE_FAILED",
                reasoning=[
                    "The AI models failed to process this subgraph or are not available."
                ],
            )

        # 3. Local Graph
        nodes = []
        # Mapping for neighbor risk scores (representative values for UI)
        risk_score_map = {
            "BENIGN": 0.0,
            "LOW_RISK": 0.3,
            "HIGH_RISK": 0.7,
            "MALICIOUS": 1.0,
        }
        neighbor_labels = (
            inference_result.get("neighbor_labels", {}) if inference_result else {}
        )

        for n_id, attrs in subgraph.nodes(data=True):
            # If this is the target node, use the inference result
            if n_id == profile_id:
                node_label = analysis.predict_label
                # Use the probability of the predicted label for node_risk
                node_risk = analysis.predict_proba.get(analysis.predict_label, 0.0)
                node_reason = (
                    "; ".join(analysis.reasoning) if analysis.reasoning else ""
                )
            else:
                # Use pre-labeled risk from graph Backbone for neighbors
                node_label = neighbor_labels.get(n_id, "BENIGN")

                # Check for risk_score in graph attributes (from rule_based_scoring_labels.csv)
                if "risk_score" in attrs and pd.notna(attrs["risk_score"]):
                    # Assuming risk_score is 0-100 in CSV, convert to 0.0-1.0
                    node_risk = float(attrs["risk_score"]) / 100.0
                else:
                    node_risk = risk_score_map.get(node_label, 0.0)

                node_reason = f"Labeled as {node_label} in Backbone."

            # Define a safe converter for numeric attributes
            def safe_float(x, default=0.0):
                return float(x) if pd.notna(x) else default

            def safe_int(x, default=0):
                return int(float(x)) if pd.notna(x) else default

            file_reason = safe_str(attrs.get("reason"), "")
            if file_reason:
                node_reason = file_reason

            nodes.append(
                LocalGraphNode(
                    id=n_id,
                    risk_label=node_label,
                    risk_score=node_risk,
                    cluster_id=safe_int(attrs.get("cluster_id"), 0),
                    attributes={
                        "handle": safe_str(attrs.get("handle"), "unknown"),
                        "trust_score": safe_float(attrs.get("trust_score")),
                        "follower_count": safe_int(attrs.get("total_followers")),
                        "following_count": safe_int(attrs.get("total_following")),
                        "post_count": safe_int(attrs.get("total_posts")),
                        "picture_url": safe_str(attrs.get("picture_url"), ""),
                        "owned_by": safe_str(attrs.get("owned_by"), ""),
                        "reason": node_reason,
                    },
                )
            )

        def safe_float(x, default=0.0):
            return float(x) if pd.notna(x) else default

        links = []
        for u, v, data in subgraph.edges(data=True):
            links.append(
                LocalGraphLink(
                    source=u,
                    target=v,
                    edge_type=data.get("edge_type", "UNKNOWN"),
                    weight=safe_float(data.get("weight"), 1.0),
                    gat_attention=safe_float(data.get("gat_attention"), 0.0),
                )
            )
        edge_type_counts = {}
        for link in links:
            edge_type_counts[link.edge_type] = (
                edge_type_counts.get(link.edge_type, 0) + 1
            )

        try:
            confidence = (
                analysis.predict_proba.get(analysis.predict_label, 0.0)
                if hasattr(analysis, "predict_proba") and analysis.predict_proba
                else 0.0
            )
            history_record = InspectorHistory(
                target_address=profile_id,
                predict_label=analysis.predict_label,
                confidence_score=confidence,
                depth_filter=2,
            )
            db.add(history_record)
            db.commit()
        except Exception as db_err:
            print(f"Failed to save prediction history: {db_err}")
            db.rollback()

        debug_payload = None
        if debug:
            debug_payload = {
                "fallback": fallback_debug,
                "subgraph_edge_type_counts": edge_type_counts,
                "co_owner_count": edge_type_counts.get("CO-OWNER", 0),
                "similarity_count": edge_type_counts.get("SIMILARITY", 0),
            }

        return InspectorProfileResponse(
            profile_info=profile_info,
            analysis=analysis,
            local_graph=LocalGraph(nodes=nodes, links=links),
            debug=debug_payload,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while extracting ego-graph: {str(e)}",
        )
