from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class ProfileInfo(BaseModel):
    id: str
    handle: Optional[str] = "unknown"
    picture_url: Optional[str] = ""
    owned_by: Optional[str] = ""


class AnalysisInfo(BaseModel):
    predict_label: str = "PENDING_AI_INFERENCE"
    predict_proba: Dict[str, float] = {}
    reasoning: List[str] = []


class LocalGraphNode(BaseModel):
    id: str
    risk_label: str = "BENIGN"
    risk_score: float = 0.0
    cluster_id: int = 0
    attributes: Dict[str, Any]


class LocalGraphLink(BaseModel):
    source: str
    target: str
    edge_type: str = "MENTION"
    weight: float = 1.0
    gat_attention: float = 0.0


class LocalGraph(BaseModel):
    nodes: List[LocalGraphNode]
    links: List[LocalGraphLink]


class InspectorProfileResponse(BaseModel):
    profile_info: ProfileInfo
    analysis: AnalysisInfo
    local_graph: LocalGraph
    debug: Optional[Dict[str, Any]] = None
