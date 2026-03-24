from __future__ import annotations

from typing import Optional, Literal

from pydantic import BaseModel


class TimeRange(BaseModel):
    start_date: str
    end_date: str


class GAEHyperparameters(BaseModel):
    max_epochs: int = 400
    patience: int = 30
    learning_rate: float = 0.005


class DiscoveryRequest(BaseModel):
    time_range: TimeRange
    max_nodes: int = 2000
    hyperparameters: Optional[GAEHyperparameters] = None


class NodeSchema(BaseModel):
    id: str
    label: str
    cluster_id: int
    risk_score: float
    attributes: dict


class LinkSchema(BaseModel):
    source: str
    target: str
    edge_type: str
    weight: float


class GraphDataSchema(BaseModel):
    nodes: list[NodeSchema]
    links: list[LinkSchema]
    cluster_count: Optional[int] = None


class DiscoveryStatusResponse(BaseModel):
    task_id: str
    status: Literal["PROCESSING", "COMPLETED", "FAILED"] = "PROCESSING"
    progress: int = 0
    current_step: str = "QUEUED"
    graph_data: Optional[GraphDataSchema] = None
    message: Optional[str] = None

