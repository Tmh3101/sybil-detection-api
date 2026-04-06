from __future__ import annotations

import modal

# from modal import Mount, asgi_app

# Phase 1: Môi trường & Kéo Dữ Liệu (Data Ingestion)
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch==2.1.2",
        index_url="https://download.pytorch.org/whl/cu121",
    )
    .pip_install(
        "torch_geometric",
        "scikit-learn",
        "networkx",
        "google-cloud-bigquery",
        "db-dtypes",
        "pandas",
        "sentence-transformers==2.7.0",
        "numpy<2.0.0",
        "transformers==4.36.2",
        "fastapi[standard]",  # Thêm cho Module 2
        "pydantic",  # Thêm cho Module 2
        "joblib",  # Thêm để load mô hình ML
        "SQLAlchemy",  # Thêm cho Database History
    )
    .run_commands(
        "python -c \"from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2', device='cpu')\""
    )
    .add_local_dir("./app", remote_path="/root/app")
    .add_local_dir("./data", remote_path="/root/data")
)

# Volume for SQLite database
db_volume = modal.Volume.from_name("sybil-db-volume", create_if_missing=True)

# Khai báo app với Secret để truy cập Google BigQuery
app = modal.App(
    "sybil-discovery-engine",
    image=image,
    secrets=[modal.Secret.from_name("gcp-sybil-secret")],
)


def sanitize_label(label: str) -> str:
    """Strip numeric prefix from risk label (e.g., '0_BENIGN' -> 'BENIGN')."""
    if "_" in label and label[0].isdigit():
        return label.split("_", 1)[1]
    return label


def fetch_bigquery_data(start_date: str, end_date: str, max_nodes: int = 2000):
    """
    Truy xuất dữ liệu đầy đủ từ Lens Protocol trên BigQuery (Tham khảo build_datasets.py).
    """
    import os
    import json
    import pandas as pd
    from google.cloud import bigquery
    from google.oauth2 import service_account

    # Đọc nội dung JSON từ Modal Secret (GOOGLE_APPLICATION_CREDENTIALS chứa JSON string)
    creds_json_str = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

    if creds_json_str:
        try:
            creds_dict = json.loads(creds_json_str)
            credentials = service_account.Credentials.from_service_account_info(
                creds_dict
            )
            client = bigquery.Client(
                credentials=credentials,
                project=creds_dict.get("project_id"),
                location="US",
            )
        except json.JSONDecodeError:
            print(
                "[Error] GOOGLE_APPLICATION_CREDENTIALS không phải là JSON hợp lệ. Thử mặc định."
            )
            client = bigquery.Client(location="US")
    else:
        client = bigquery.Client(location="US")

    # SQL lấy danh sách tài khoản (Nodes) kèm theo đầy đủ đặc trưng on-chain
    query_nodes = f"""
    SELECT
        `lens-protocol-mainnet.app.FORMAT_HEX`(meta.account) as profile_id,
        ANY_VALUE(meta.created_on) as created_on,
        ANY_VALUE(meta.name) as display_name,
        ANY_VALUE(meta.metadata) as raw_metadata,
        ANY_VALUE(`lens-protocol-mainnet.app.FORMAT_HEX`(ksw.owned_by)) as owned_by,
        ARRAY_AGG(usr.local_name ORDER BY usr.timestamp DESC LIMIT 1)[OFFSET(0)] as handle,
        ARRAY_AGG(score.score ORDER BY score.generated_at DESC LIMIT 1)[OFFSET(0)] as trust_score,
        -- Thống kê hành vi on-chain
        ANY_VALUE(ps.total_posts) as total_posts,
        ANY_VALUE(ps.total_comments) as total_comments,
        ANY_VALUE(ps.total_reposts) as total_reposts,
        ANY_VALUE(ps.total_collects) as total_collects,
        ANY_VALUE(ps.total_tips) as total_tips,
        ANY_VALUE(ps.total_quotes) as total_quotes,
        ANY_VALUE(ps.total_reacted) as total_reacted,
        ANY_VALUE(ps.total_reactions) as total_reactions,
        ANY_VALUE(fs.total_followers) as total_followers,
        ANY_VALUE(fs.total_following) as total_following
    FROM `lens-protocol-mainnet.account.metadata` as meta
    LEFT JOIN `lens-protocol-mainnet.username.record` as usr
        ON meta.account = usr.account
    LEFT JOIN `lens-protocol-mainnet.account.known_smart_wallet` as ksw
        ON meta.account = ksw.address
    LEFT JOIN `lens-protocol-mainnet.ml.account_score` as score
        ON meta.account = score.account
    LEFT JOIN `lens-protocol-mainnet.account.post_summary` as ps
        ON meta.account = ps.account
    LEFT JOIN `lens-protocol-mainnet.account.follower_summary` as fs
        ON meta.account = fs.account
    WHERE meta.created_on >= '{start_date}'
      AND meta.created_on < '{end_date}'
    GROUP BY 1
    ORDER BY ANY_VALUE(meta.created_on) DESC
    LIMIT {max_nodes}
    """

    # SQL lấy quan hệ Follow thực tế
    query_edges_follow = f"""
    WITH TargetUsers AS (
        SELECT account
        FROM `lens-protocol-mainnet.account.metadata`
        WHERE created_on >= '{start_date}'
          AND created_on < '{end_date}'
        ORDER BY created_on DESC
        LIMIT {max_nodes}
    )
    SELECT DISTINCT
        `lens-protocol-mainnet.app.FORMAT_HEX`(f.account_follower) as source,
        `lens-protocol-mainnet.app.FORMAT_HEX`(f.account_following) as target,
        'FOLLOW' as type
    FROM `lens-protocol-mainnet.account.follower` as f
    JOIN TargetUsers as t1 ON f.account_follower = t1.account
    JOIN TargetUsers as t2 ON f.account_following = t2.account
    """

    # SQL lấy quan hệ Interaction (Comment/Quote)
    query_edges_interact = f"""
    WITH TargetUsers AS (
        SELECT account
        FROM `lens-protocol-mainnet.account.metadata`
        WHERE created_on >= '{start_date}'
          AND created_on < '{end_date}'
        ORDER BY created_on DESC
        LIMIT {max_nodes}
    )
    SELECT
        `lens-protocol-mainnet.app.FORMAT_HEX`(p.account) as source,
        `lens-protocol-mainnet.app.FORMAT_HEX`(parent.account) as target,
        CASE WHEN p.parent_post IS NOT NULL THEN 'COMMENT' ELSE 'QUOTE' END as type
    FROM `lens-protocol-mainnet.post.record` as p
    JOIN `lens-protocol-mainnet.post.record` as parent ON (p.parent_post = parent.id OR p.quoted_post = parent.id)
    JOIN TargetUsers t1 ON p.account = t1.account
    JOIN TargetUsers t2 ON parent.account = t2.account
    WHERE p.timestamp >= '{start_date}' AND p.timestamp < '{end_date}'
      AND p.account != parent.account
    """

    df_nodes = client.query(query_nodes).to_dataframe()
    df_edges_follow = client.query(query_edges_follow).to_dataframe()
    df_edges_interact = client.query(query_edges_interact).to_dataframe()

    df_edges = pd.concat([df_edges_follow, df_edges_interact], ignore_index=True)

    # Calculate days_active
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    df_nodes["created_on"] = pd.to_datetime(df_nodes["created_on"], utc=True)
    df_nodes["days_active"] = (
        (now - df_nodes["created_on"]).dt.days.fillna(0).astype(float)
    )

    # Tích hợp hàm parse_metadata
    import ast

    def parse_metadata(meta_str):
        if pd.isna(meta_str) or not meta_str:
            return ("", "")  # Trả về tuple thay vì pd.Series
        try:
            # Đảm bảo parse chuỗi an toàn
            meta = ast.literal_eval(str(meta_str)).get("lens", {})
            return (meta.get("bio", "") or "", meta.get("picture", "") or "")
        except Exception:
            return ("", "")

    print(df_nodes.head())

    # Bắt buộc check DataFrame rỗng trước khi xử lý cột
    if df_nodes.empty:
        df_nodes["bio"] = ""
        df_nodes["picture_url"] = ""
        df_nodes["has_avatar"] = 0
    elif "raw_metadata" in df_nodes.columns:
        # Parse data thành list các tuples
        parsed_data = df_nodes["raw_metadata"].apply(parse_metadata)

        # Tách an toàn vào từng cột
        df_nodes["bio"] = [x[0] for x in parsed_data]
        df_nodes["picture_url"] = [x[1] for x in parsed_data]

        # Cập nhật lại cột has_avatar dựa trên picture_url
        df_nodes["has_avatar"] = df_nodes["picture_url"].apply(
            lambda x: 1 if (x and x != "") else 0
        )
    else:
        # Fallback an toàn nếu không tìm thấy cột
        df_nodes["bio"] = ""
        df_nodes["picture_url"] = ""
        df_nodes["has_avatar"] = 0

    # Xử lý các giá trị null trong node features
    cols_to_fix = [
        "total_posts",
        "total_comments",
        "total_reposts",
        "total_collects",
        "total_followers",
        "total_following",
        "total_tips",
        "total_quotes",
        "total_reacted",
        "total_reactions",
        "trust_score",
    ]
    df_nodes[cols_to_fix] = df_nodes[cols_to_fix].fillna(0)

    return df_nodes, df_edges


def build_pyg_graph(df_nodes, df_edges):
    """
    Xây dựng đồ thị PyTorch Geometric (Full Feature Concatenation).
    Refactored to prune isolated nodes before feature extraction.
    """
    import torch
    import numpy as np
    import pandas as pd
    import itertools
    import math
    from collections import defaultdict
    from sentence_transformers import SentenceTransformer
    from torch_geometric.data import Data
    from sklearn.preprocessing import MinMaxScaler

    # --- STEP 1: Reorder Edge Logic (Identify all potential edges) ---
    edges_list = []

    # 1.1 Existing edges from BigQuery (Follow/Interact)
    # Step 1: Đếm số lần tương tác cùng loại giữa cùng cặp node
    interaction_counts = defaultdict(int)
    for _, row in df_edges.iterrows():
        key = (row["source"], row["target"], row["type"])
        interaction_counts[key] += 1

    BASE_WEIGHTS_LOCAL = {
        "FOLLOW": 1.0,
        "UPVOTE": 1.0,
        "REACTION": 1.0,
        "COMMENT": 2.0,
        "QUOTE": 2.0,
        "MIRROR": 3.0,
        "COLLECT": 4.0,
        "TIP": 4.0,
    }
    DIRECTED_TYPES = set(BASE_WEIGHTS_LOCAL.keys())

    # Step 2: Tạo edges với log-weight (1 cạnh duy nhất mỗi cặp-type)
    edges_list = []
    seen = set()
    for _, row in df_edges.iterrows():
        key = (row["source"], row["target"], row["type"])
        if key in seen:
            continue
        seen.add(key)

        n = interaction_counts[key]
        base = BASE_WEIGHTS_LOCAL.get(row["type"], 1.0)
        log_weight = base * (1 + math.log10(max(1, n)))

        edges_list.append(
            {
                "source": row["source"],
                "target": row["target"],
                "type": row["type"],
                "weight": log_weight,
            }
        )

        # Step 3: Sinh REV edge cho directed edges
        if row["type"] in DIRECTED_TYPES:
            edges_list.append(
                {
                    "source": row["target"],
                    "target": row["source"],
                    "type": row["type"] + "_REV",
                    "weight": log_weight * 0.5,
                }
            )

    # 1.2 CO-OWNER edges (Logic Python)
    df_owned = df_nodes[df_nodes["owned_by"].notnull()]
    for _, group in df_owned.groupby("owned_by"):
        if len(group) > 1:
            pids = group["profile_id"].tolist()
            for src, dst in itertools.combinations(pids, 2):
                edges_list.append(
                    {"source": src, "target": dst, "type": "CO-OWNER", "weight": 5.0}
                )

    # 1.3 SIMILARITY edges (Close Creation Time)
    df_nodes["created_dt"] = pd.to_datetime(df_nodes["created_on"])
    df_sorted = df_nodes.sort_values("created_dt")
    for i in range(len(df_sorted) - 1):
        diff = (
            df_sorted.iloc[i + 1]["created_dt"] - df_sorted.iloc[i]["created_dt"]
        ).total_seconds()
        if diff < 5:
            edges_list.append(
                {
                    "source": df_sorted.iloc[i]["profile_id"],
                    "target": df_sorted.iloc[i + 1]["profile_id"],
                    "type": "SIMILARITY",
                    "weight": 3.0,
                }
            )

    # --- STEP 2: Identify Connected Nodes ---
    connected_node_ids = set()
    for e in edges_list:
        connected_node_ids.add(e["source"])
        connected_node_ids.add(e["target"])

    # --- STEP 3: Prune DataFrame ---
    # Keep only nodes that have at least one edge and are present in df_nodes
    all_available_pids = set(df_nodes["profile_id"])
    valid_connected_nodes = connected_node_ids.intersection(all_available_pids)
    df_nodes_pruned = df_nodes[
        df_nodes["profile_id"].isin(valid_connected_nodes)
    ].copy()

    # --- STEP 4: Re-index node mapping based on pruned nodes ---
    node_ids = df_nodes_pruned["profile_id"].tolist()
    id_to_idx = {pid: i for i, pid in enumerate(node_ids)}

    # --- STEP 5: Clean Edges: filter out edges that reference pruned nodes (safeguard) ---
    edges_list = [
        e for e in edges_list if e["source"] in id_to_idx and e["target"] in id_to_idx
    ]

    # --- STEP 6: Optimized Feature Extraction (only on connected nodes) ---
    if df_nodes_pruned.empty:
        # Return empty data if no connected nodes found
        return (
            Data(
                x=torch.empty((0, 396)),
                edge_index=torch.empty((2, 0), dtype=torch.long),
            ),
            [],
            [],
        )

    model = SentenceTransformer("all-MiniLM-L6-v2")
    text_data = []
    onchain_features_raw = []

    for _, row in df_nodes_pruned.iterrows():
        # Text: Sử dụng cột 'bio' đã được parse sẵn từ fetch_bigquery_data
        bio = row["bio"] if (pd.notnull(row["bio"]) and row["bio"] != "") else ""
        handle = row["handle"] or "unknown"
        name = row["display_name"] or "unknown"
        text_data.append(f"Handle: {handle}. Name: {name}. Bio: {bio}")

        # On-chain raw: 12 features in specific order (matching research pipeline)
        onchain_features_raw.append(
            [
                float(row["trust_score"]),
                float(row["total_tips"]),
                float(row["total_posts"]),
                float(row["total_quotes"]),
                float(row["total_reacted"]),
                float(row["total_reactions"]),
                float(row["total_reposts"]),
                float(row["total_collects"]),
                float(row["total_comments"]),
                float(row["total_followers"]),
                float(row["total_following"]),
                float(row["days_active"]),
            ]
        )

    # Encode văn bản (Expensive step)
    tensor_text = torch.tensor(model.encode(text_data), dtype=torch.float)

    # Chuẩn hóa On-chain features
    scaler = MinMaxScaler()
    onchain_scaled = scaler.fit_transform(np.array(onchain_features_raw))
    tensor_onchain = torch.tensor(onchain_scaled, dtype=torch.float)

    # NỐI ĐẶC TRƯNG: 384 (text) + 12 (on-chain) = 396 chiều
    x = torch.cat([tensor_text, tensor_onchain], dim=1)

    # --- STEP 7: Build PyG Data ---
    edge_sources = [id_to_idx[e["source"]] for e in edges_list]
    edge_targets = [id_to_idx[e["target"]] for e in edges_list]
    edge_index = torch.tensor([edge_sources, edge_targets], dtype=torch.long)
    edge_attr = torch.tensor([e["weight"] for e in edges_list], dtype=torch.float).view(
        -1, 1
    )

    data = Data(x=x, edge_index=edge_index, edge_attr=edge_attr)

    return data, node_ids, edges_list


@app.function(gpu="T4", timeout=1800)
def train_gae_pipeline(payload: dict) -> dict:
    """
    Module 1 worker pipeline (Fixed Ingestion & Engineering):
    """
    import torch
    import torch.nn.functional as F
    from torch_geometric.nn import GATv2Conv, GAE
    from sklearn.cluster import KMeans
    import pandas as pd

    class GATEncoder(torch.nn.Module):
        def __init__(self, in_channels, out_channels=16):
            super().__init__()
            self.conv1 = GATv2Conv(in_channels, 32, heads=4, dropout=0.1, edge_dim=1)
            self.conv2 = GATv2Conv(
                32 * 4, out_channels, heads=1, concat=False, dropout=0.1, edge_dim=1
            )

        def forward(self, x, edge_index, edge_attr):
            x = self.conv1(x, edge_index, edge_attr=edge_attr)
            x = F.elu(x)
            x = F.dropout(x, p=0.1, training=self.training)
            x = self.conv2(x, edge_index, edge_attr=edge_attr)
            return x

    # 1) Parse
    time_range = payload.get("time_range", {})
    start_date = time_range.get("start_date", "2025-12-01 00:00:00")
    end_date = time_range.get("end_date", "2025-12-07 00:00:00")

    # Hyperparameters from payload
    max_nodes = max(100, min(payload.get("max_nodes", 2000), 5000))
    hp = payload.get("hyperparameters") or {}
    max_epochs = max(50, min(hp.get("max_epochs", 400), 1000))
    patience = max(10, min(hp.get("patience", 30), 100))
    learning_rate = max(0.0001, min(hp.get("learning_rate", 0.005), 0.01))

    # 2) Fetch Data (Respecting max_nodes)
    df_nodes, df_edges = fetch_bigquery_data(start_date, end_date, max_nodes=max_nodes)
    if df_nodes.empty:
        return {"nodes": [], "links": []}

    # 3) Build PyG graph (Feature Concatenation)
    data, profile_ids, edges_list = build_pyg_graph(df_nodes, df_edges)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Smart Early Stopping variables
    best_loss = float("inf")
    patience_counter = 0
    best_weights = None

    # 4) Train GAE
    model = GAE(GATEncoder(in_channels=data.num_features, out_channels=16)).to(device)
    data = data.to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)

    model.train()
    for epoch in range(max_epochs):
        optimizer.zero_grad()
        z = model.encode(data.x, data.edge_index, data.edge_attr)
        loss = model.recon_loss(z, data.edge_index)
        loss.backward()
        optimizer.step()

        # Early Stopping check
        current_loss = loss.item()
        if current_loss < best_loss:
            best_loss = current_loss
            patience_counter = 0
            best_weights = {k: v.cpu().clone() for k, v in model.state_dict().items()}
        else:
            patience_counter += 1

        if patience_counter >= patience:
            print(f"[GAE] Early stopping triggered at epoch {epoch}")
            break

    # Restore Best Weights
    if best_weights is not None:
        model.load_state_dict({k: v.to(device) for k, v in best_weights.items()})

    model.eval()
    with torch.no_grad():
        node_embeddings = (
            model.encode(data.x, data.edge_index, data.edge_attr).cpu().numpy()
        )

    # 5) KMeans & Heuristics (Cluster-level Scoring)
    num_nodes = data.num_nodes
    if num_nodes > 0:
        import math

        # Apply interpolation formula based on 300-node benchmark
        calculated_k = int(21 * math.sqrt(num_nodes / 300.0))
        # Ensure K is at least 1, and no greater than the total number of nodes
        n_clusters = max(1, min(num_nodes, calculated_k))
    else:
        n_clusters = 1

    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    cluster_ids = kmeans.fit_predict(node_embeddings)

    # Step 1: Map Nodes to Clusters
    pid_to_cluster = {pid: cluster_ids[i] for i, pid in enumerate(profile_ids)}

    # Step 2: Filter Internal Edges
    from collections import defaultdict

    cluster_internal_edges = defaultdict(list)
    for e in edges_list:
        src_cluster = pid_to_cluster.get(e["source"])
        dst_cluster = pid_to_cluster.get(e["target"])
        if src_cluster is not None and src_cluster == dst_cluster:
            cluster_internal_edges[src_cluster].append(e)

    # Step 3 & 4: Calculate Cluster Statistics & Risk Scoring
    cluster_stats = {}
    df_nodes["created_dt"] = pd.to_datetime(df_nodes["created_on"], utc=True)

    for c_id in range(n_clusters):
        # Nodes in this cluster
        c_nodes_indices = [i for i, cid in enumerate(cluster_ids) if cid == c_id]
        c_pids = [profile_ids[i] for i in c_nodes_indices]
        c_df = df_nodes[df_nodes["profile_id"].isin(c_pids)]

        size = len(c_nodes_indices)
        internal_edges = cluster_internal_edges[c_id]

        # Tính intensity percentage (dựa trên tổng WEIGHT, không phải count)
        total_weight = sum(e["weight"] for e in internal_edges) or 1.0

        co_owner_weight = sum(
            e["weight"] for e in internal_edges if e["type"] == "CO-OWNER"
        )
        similarity_weight = sum(
            e["weight"]
            for e in internal_edges
            if e["type"] in ["SIM_BIO", "FUZZY_HANDLE", "CLOSE_CREATION_TIME"]
        )
        social_weight = sum(
            e["weight"]
            for e in internal_edges
            if e["type"] in ["FOLLOW", "COMMENT", "QUOTE", "UPVOTE", "COLLECT", "TIP"]
        )
        fuzzy_weight = sum(
            e["weight"] for e in internal_edges if e["type"] == "FUZZY_HANDLE"
        )

        pct_co_owner = co_owner_weight / total_weight
        pct_similarity = similarity_weight / total_weight
        pct_social = social_weight / total_weight
        pct_fuzzy = fuzzy_weight / total_weight

        avg_trust = c_df["trust_score"].mean() if not c_df.empty else 0

        if size > 1:
            std_creation_hours = c_df["created_dt"].std().total_seconds() / 3600.0
        else:
            std_creation_hours = 0

        # Scoring với ngưỡng mới
        score = 0
        reasons = []

        if pct_co_owner > 0.15:  # Thay từ 0.10
            score += 40  # Thay từ 50
            reasons.append(f"High Co-owner intensity ({pct_co_owner:.1%}) +40")

        if pct_similarity >= 0.50:  # Thay từ 0.60
            score += 30
            reasons.append(f"High Similarity intensity ({pct_similarity:.1%}) +30")

        if size > 1 and std_creation_hours < 0.5:
            score += 15
            reasons.append(f"Batch Creation (std: {std_creation_hours:.2f}h) +15")

        if pct_fuzzy >= 0.50:
            score += 15
            reasons.append(f"Fuzzy Handle pattern ({pct_fuzzy:.1%}) +15")

        if pct_social <= 0.15:  # Thay từ 0.20
            score += 10
            reasons.append(f"Low Social intensity ({pct_social:.1%}) +10")

        if avg_trust <= 5:
            score += 20
            reasons.append(f"Very Low Trust ({avg_trust:.2f}) +20")
        elif avg_trust <= 10:  # Thay từ 8
            score += 10
            reasons.append(f"Low Trust ({avg_trust:.2f}) +10")

        score = min(100, score)
        risk_score = score / 100.0

        # Fuzzy Labeling
        if score < 20:
            label = "0_BENIGN"
        elif score <= 50:
            label = "1_LOW_RISK"
        elif score < 80:
            label = "2_HIGH_RISK"
        else:
            label = "3_MALICIOUS"

        cluster_stats[c_id] = {
            "label": sanitize_label(label),
            "risk_score": risk_score,
            "reasons": reasons,
        }

    # 6) Format
    nodes = []
    for i, pid in enumerate(profile_ids):
        node_row = df_nodes[df_nodes["profile_id"] == pid].iloc[0]
        c_id = cluster_ids[i]
        c_info = cluster_stats[c_id]

        nodes.append(
            {
                "id": pid,
                "risk_label": c_info["label"],
                "cluster_id": int(c_id),
                "risk_score": float(c_info["risk_score"]),
                "attributes": {
                    "handle": node_row["handle"] or "unknown",
                    "trust_score": (
                        float(node_row["trust_score"])
                        if pd.notnull(node_row["trust_score"])
                        else 0.0
                    ),
                    "follower_count": (
                        int(node_row["total_followers"])
                        if pd.notnull(node_row["total_followers"])
                        else 0
                    ),
                    "post_count": (
                        int(node_row["total_posts"])
                        if pd.notnull(node_row["total_posts"])
                        else 0
                    ),
                    "picture_url": (
                        str(node_row["picture_url"])
                        if pd.notnull(node_row["picture_url"])
                        else None
                    ),
                    "owned_by": (
                        str(node_row["owned_by"])
                        if pd.notnull(node_row["owned_by"])
                        else None
                    ),
                    "reasons": c_info["reasons"],
                },
            }
        )

    links = []
    for e in edges_list:
        links.append(
            {
                "source": e["source"],
                "target": e["target"],
                "edge_type": e["type"],
                "weight": float(e["weight"]),
            }
        )

    return {
        "cluster_count": int(n_clusters),
        "num_nodes": len(nodes),
        "num_edges": len(links),
        "nodes": nodes,
        "links": links,
        "start_date": start_date,
        "end_date": end_date,
    }


@app.function(
    image=image,
    gpu="T4",
    memory=4096,  # Cấp 4GB RAM cho việc chứa Graph và Model AI
    # keep_warm=1,
    startup_timeout=300,  # Chống timeout khi load file Backbone và Models nặng
    secrets=[modal.Secret.from_name("gcp-sybil-secret")],
    volumes={"/data/db": db_volume},
)
@modal.asgi_app()
def fastapi_endpoint():
    """
    Module 2 worker pipeline (Real-time Inference):
    Khởi chạy ứng dụng FastAPI, tự động kích hoạt lifespan để nạp Graph và AI Models.
    """
    from app.main import app as web_app

    return web_app


# Deploy: modal deploy modal_worker/app.py
