from __future__ import annotations

import random

import modal

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch==2.1.2",
        index_url="https://download.pytorch.org/whl/cu121",
    )
    .pip_install("torch_geometric", "scikit-learn", "networkx")
)

app = modal.App("sybil-discovery-engine", image=image)


@app.function(gpu="T4", timeout=1800)
def train_gae_pipeline(payload: dict) -> dict:
    """
    Module 1 worker pipeline (skeleton):
    1) Parse request payload
    2) Create a small dummy transaction graph
    3) Build node embeddings (mocked for now, GAE-ready structure)
    4) Cluster embeddings with KMeans
    5) Return graph data JSON for backend/UI
    """
    # IMPORTANT: lazy imports so local CLI/client does not require ML deps.
    import networkx as nx
    import torch
    from sklearn.cluster import KMeans
    from torch_geometric.nn import GATConv

    # 1) Read request payload (fallback defaults keep worker resilient).
    time_range = payload.get("time_range", {})
    _start_date = time_range.get("start_date")
    _end_date = time_range.get("end_date")
    max_nodes = int(payload.get("max_nodes", 30))
    num_nodes = max(8, min(max_nodes, 30))

    # 2) Build a small dummy graph to mimic Web3 transaction interactions.
    graph = nx.gnm_random_graph(n=num_nodes, m=max(num_nodes, num_nodes * 2), seed=42)
    graph = graph.to_directed()
    for src, dst in graph.edges():
        graph[src][dst]["weight"] = round(random.uniform(0.1, 1.0), 3)
        graph[src][dst]["edge_type"] = random.choice(["transfer", "swap", "bridge"])

    # 3) Create embeddings skeleton.
    # Keep a reference to GATConv so this script is ready for real GAE training.
    _gat = GATConv(in_channels=8, out_channels=8, heads=1, concat=False)
    _ = _gat

    # For now we simulate learned embeddings using random tensors.
    torch.manual_seed(42)
    embeddings = torch.randn(num_nodes, 8)

    # 4) KMeans clustering on embeddings.
    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
    cluster_ids = kmeans.fit_predict(embeddings.detach().cpu().numpy())

    # 5) Map to backend GraphDataSchema-compatible output.
    nodes = []
    for node_id in graph.nodes():
        risk_score = float(min(0.99, abs(float(embeddings[node_id][0])) / 2.0))
        label = "HIGH_RISK" if risk_score >= 0.7 else "BENIGN"
        nodes.append(
            {
                "id": f"node-{node_id}",
                "label": label,
                "cluster_id": int(cluster_ids[node_id]),
                "risk_score": risk_score,
                "attributes": {
                    "address": f"0x{node_id:04x}",
                    "tx_count": int(graph.degree(node_id)),
                },
            }
        )

    links = []
    for src, dst, attrs in graph.edges(data=True):
        links.append(
            {
                "source": f"node-{src}",
                "target": f"node-{dst}",
                "edge_type": attrs.get("edge_type", "transfer"),
                "weight": float(attrs.get("weight", 0.5)),
            }
        )

    return {"nodes": nodes, "links": links}
