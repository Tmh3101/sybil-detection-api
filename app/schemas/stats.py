from pydantic import BaseModel
from typing import Dict, List

class EdgeDistributionItem(BaseModel):
    layer: str
    count: int
    percentage: float

class OverviewResponse(BaseModel):
    total_nodes: int
    total_edges: int
    edge_distribution: List[EdgeDistributionItem]

class RiskDistributionItem(BaseModel):
    label: str
    count: int
    percentage: float

class RiskDistributionResponse(BaseModel):
    distribution: List[RiskDistributionItem]

class TrustScoreBin(BaseModel):
    range_label: str   # "0-10", "10-20", ...
    count: int

class TrustScoreResponse(BaseModel):
    bins: List[TrustScoreBin]
    mean: float
    median: float

class ClusterStatsResponse(BaseModel):
    total_clusters: int
    avg_cluster_size: float
    largest_cluster: int
    smallest_cluster: int