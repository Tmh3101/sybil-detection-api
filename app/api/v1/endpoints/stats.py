from fastapi import APIRouter, Request, HTTPException, status
from collections import Counter, defaultdict
import numpy as np

from app.schemas.stats import (
    OverviewResponse,
    EdgeDistributionItem,
    RiskDistributionResponse,
    RiskDistributionItem,
    TrustScoreResponse,
    TrustScoreBin,
    ClusterStatsResponse,
)

router = APIRouter()

LABEL_MAP = {0: "BENIGN", 1: "LOW_RISK", 2: "HIGH_RISK", 3: "MALICIOUS"}

EDGE_LAYER_MAP = {
    "FOLLOW": "Follow",
    "FOLLOW_REV": "Follow",
    "UPVOTE": "Interact",
    "UPVOTE_REV": "Interact",
    "REACTION": "Interact",
    "REACTION_REV": "Interact",
    "COMMENT": "Interact",
    "COMMENT_REV": "Interact",
    "QUOTE": "Interact",
    "QUOTE_REV": "Interact",
    "MIRROR": "Interact",
    "MIRROR_REV": "Interact",
    "COLLECT": "Interact",
    "COLLECT_REV": "Interact",
    "TIP": "Interact",
    "TIP_REV": "Interact",
    "CO-OWNER": "Co-Owner",
    "SIMILARITY": "Similarity",
    "FUZZY_HANDLE": "Similarity",
    "SIM_BIO": "Similarity",
    "CLOSE_CREATION_TIME": "Similarity",
}


def _get_graph(request: Request):
    if not hasattr(request.app.state, "graph"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Graph Backbone not initialized.",
        )
    return request.app.state.graph


@router.get("/overview", response_model=OverviewResponse)
async def get_overview(request: Request):
    G = _get_graph(request)
    total_nodes = G.number_of_nodes()
    total_edges = G.number_of_edges()

    # Đếm theo layer
    layer_counts: dict = defaultdict(int)
    for u, v, data in G.edges(data=True):
        e_type = data.get("type", "UNKNOWN")
        layer = EDGE_LAYER_MAP.get(e_type, "Other")
        layer_counts[layer] += 1

    distribution = [
        EdgeDistributionItem(
            layer=layer,
            count=count,
            percentage=round(count / total_edges * 100, 2) if total_edges else 0,
        )
        for layer, count in sorted(
            layer_counts.items(), key=lambda x: x[1], reverse=True
        )
    ]

    return OverviewResponse(
        total_nodes=total_nodes,
        total_edges=total_edges,
        edge_distribution=distribution,
    )


@router.get("/risk-distribution", response_model=RiskDistributionResponse)
async def get_risk_distribution(request: Request):
    G = _get_graph(request)
    label_counts: dict = Counter()

    for _, attrs in G.nodes(data=True):
        label_idx = attrs.get("label", 0)
        label_name = LABEL_MAP.get(int(label_idx), "UNKNOWN")
        label_counts[label_name] += 1

    total = sum(label_counts.values()) or 1
    all_labels = ["BENIGN", "LOW_RISK", "HIGH_RISK", "MALICIOUS"]

    distribution = [
        RiskDistributionItem(
            label=label,
            count=label_counts.get(label, 0),
            percentage=round(label_counts.get(label, 0) / total * 100, 2),
        )
        for label in all_labels
    ]

    return RiskDistributionResponse(distribution=distribution)


@router.get("/trust-scores", response_model=TrustScoreResponse)
async def get_trust_scores(request: Request):
    G = _get_graph(request)
    scores = [
        float(attrs.get("trust_score", 0))
        for _, attrs in G.nodes(data=True)
        if attrs.get("trust_score") is not None
    ]

    if not scores:
        return TrustScoreResponse(bins=[], mean=0.0, median=0.0)

    # Tạo 10 bins: 0-10, 10-20, ..., 90-100
    bins = []
    for i in range(10):
        lo, hi = i * 10, (i + 1) * 10
        count = sum(1 for s in scores if lo <= s < hi)
        bins.append(TrustScoreBin(range_label=f"{lo}-{hi}", count=count))
    # Bin cuối bao gồm điểm = 100
    bins[-1] = TrustScoreBin(
        range_label="90-100", count=sum(1 for s in scores if 90 <= s <= 100)
    )

    return TrustScoreResponse(
        bins=bins,
        mean=round(float(np.mean(scores)), 2),
        median=round(float(np.median(scores)), 2),
    )


@router.get("/clusters", response_model=ClusterStatsResponse)
async def get_cluster_stats(request: Request):
    G = _get_graph(request)
    cluster_counts: dict = defaultdict(int)

    for _, attrs in G.nodes(data=True):
        # Ưu tiên cluster_id thực tế từ K-Means
        cid = attrs.get("cluster_id")

        # Nếu node không thuộc cụm nào (ví dụ node mới add qua fallback),
        # ta tạm thời bỏ qua hoặc gom vào nhóm 'unknown'
        if cid is not None:
            cluster_counts[int(cid)] += 1

    if not cluster_counts:
        # Nếu Backbone chưa có cluster_id, fallback về label để tránh trả về 0
        # nhưng log cảnh báo để dev biết
        for _, attrs in G.nodes(data=True):
            cid = attrs.get("label", 0)
            cluster_counts[int(cid)] += 1

    if not cluster_counts:
        return ClusterStatsResponse(
            total_clusters=0,
            avg_cluster_size=0.0,
            largest_cluster=0,
            smallest_cluster=0,
        )

    sizes = list(cluster_counts.values())

    return ClusterStatsResponse(
        total_clusters=len(cluster_counts),
        avg_cluster_size=round(sum(sizes) / len(sizes), 2),
        largest_cluster=max(sizes),
        smallest_cluster=min(sizes),
    )
