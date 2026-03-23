from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class ProfileInfo(BaseModel):
    id: str
    handle: Optional[str] = "unknown"
    picture_url: Optional[str] = ""
    owned_by: Optional[str] = ""

class AnalysisInfo(BaseModel):
    sybil_probability: Optional[float] = None
    classification: str = "PENDING_AI_INFERENCE"
    reasoning: List[str] = []

class LocalGraphNode(BaseModel):
    id: str
    attributes: Dict[str, Any]

class LocalGraphLink(BaseModel):
    source: str
    target: str
    edge_type: str = "MENTION"
    weight: float = 1.0

class LocalGraph(BaseModel):
    nodes: List[LocalGraphNode]
    links: List[LocalGraphLink]

class InspectorProfileResponse(BaseModel):
    profile_info: ProfileInfo
    analysis: AnalysisInfo
    local_graph: LocalGraph
