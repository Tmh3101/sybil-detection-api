import torch
import numpy as np
import pandas as pd
from datetime import datetime, timezone
import logging
import networkx as nx
from collections import Counter

# Re-use EDGE_WEIGHTS from fallback_service to maintain consistency
from app.services.fallback_service import EDGE_WEIGHTS

logger = logging.getLogger(__name__)

LABEL_MAP = {
    0: "BENIGN",
    1: "LOW_RISK",
    2: "HIGH_RISK",
    3: "MALICIOUS"
}

async def evaluate_subgraph(models: dict, subgraph: nx.MultiDiGraph, target_id: str):
    """
    Perform Hybrid AI inference on a given ego-graph.
    
    Quy trình 100% đồng bộ với training:
    1. Preprocessing Numeric Features (12 cols) -> feature_scaler
    2. NLP Embeddings (384 dim) -> nlp_model
    3. Concat -> GAT (16 dim embedding output)
    4. GAT Embedding -> embedding_scaler
    5. Scaled Embedding -> Random Forest (Classifier)
    """
    if not models or not models.get("gat_model") or not models.get("rf_model"):
        logger.error("Inference models not loaded properly.")
        return None

    # 1. Prepare Nodes & Index Mapping
    # Ensure consistent index order for all tensors
    node_list = list(subgraph.nodes())
    try:
        target_idx = node_list.index(target_id)
    except ValueError:
        logger.error(f"Target node {target_id} not found in subgraph.")
        return None

    N = len(node_list)
    now = datetime.now(timezone.utc)
    
    # --- A. Numeric Features (Nx12) ---
    # Column order MUST BE: ['trust_score', 'total_tips', 'total_posts', 'total_quotes', 
    # 'total_reacted', 'total_reactions', 'total_reposts', 'total_collects', 
    # 'total_comments', 'total_followers', 'total_following', 'days_active']
    
    numeric_data = []
    for n_id in node_list:
        attrs = subgraph.nodes[n_id]
        
        # Calculate days_active
        created_on = attrs.get("created_on")
        days_active = 0
        if created_on:
            try:
                # Handle both string and datetime objects
                created_dt = pd.to_datetime(created_on)
                if created_dt.tzinfo is None:
                    created_dt = created_dt.replace(tzinfo=timezone.utc)
                days_active = (now - created_dt).days
            except Exception:
                days_active = 0
            
        stats = [
            float(attrs.get("trust_score", 0.0) or 0.0),
            float(attrs.get("total_tips", 0.0) or 0.0),
            float(attrs.get("total_posts", 0.0) or 0.0),
            float(attrs.get("total_quotes", 0.0) or 0.0),
            float(attrs.get("total_reacted", 0.0) or 0.0),
            float(attrs.get("total_reactions", 0.0) or 0.0),
            float(attrs.get("total_reposts", 0.0) or 0.0),
            float(attrs.get("total_collects", 0.0) or 0.0),
            float(attrs.get("total_comments", 0.0) or 0.0),
            float(attrs.get("total_followers", 0.0) or 0.0),
            float(attrs.get("total_following", 0.0) or 0.0),
            float(max(0, days_active))
        ]
        numeric_data.append(stats)

    # Scale numeric features
    numeric_np = np.array(numeric_data)
    if models.get("feature_scaler"):
        try:
            numeric_scaled = models["feature_scaler"].transform(numeric_np)
        except Exception as e:
            logger.error(f"Error scaling numeric features: {e}")
            numeric_scaled = numeric_np
    else:
        numeric_scaled = numeric_np
    
    numeric_tensor = torch.tensor(numeric_scaled, dtype=torch.float)

    # --- B. Text Embeddings (Nx384) ---
    texts = []
    for n_id in node_list:
        attrs = subgraph.nodes[n_id]
        handle = attrs.get("handle") or "unknown"
        # If display_name is missing, fallback to handle or space to avoid 'None'
        display_name = attrs.get("display_name") or attrs.get("handle") or " "
        bio = attrs.get("bio") or ""
        
        # MANDATORY SYNTAX: Handle: {handle}. Name: {display_name}. Bio: {bio}
        text = f"Handle: {handle}. Name: {display_name}. Bio: {bio}"
        texts.append(text)
    
    if models.get("nlp_model"):
        try:
            # sentence_transformers.encode returns a numpy array or tensor
            text_emb = models["nlp_model"].encode(texts, convert_to_tensor=True)
            text_tensor = text_emb.to(torch.float32)
        except Exception as e:
            logger.error(f"Error encoding texts: {e}")
            text_tensor = torch.zeros((N, 384))
    else:
        text_tensor = torch.zeros((N, 384))

    # --- C. Concat Node Features (X) [N, 396] ---
    x = torch.cat([numeric_tensor, text_tensor], dim=1)
    
    # 2. Prepare Edges
    src_indices = []
    dst_indices = []
    weights = []
    
    node_to_idx = {n_id: i for i, n_id in enumerate(node_list)}
    
    for u, v, data in subgraph.edges(data=True):
        if u in node_to_idx and v in node_to_idx:
            src_indices.append(node_to_idx[u])
            dst_indices.append(node_to_idx[v])
            
            # Use weight from data if present, else lookup from EDGE_WEIGHTS
            weight = data.get("weight")
            if weight is None:
                e_type = data.get("type", "UNKNOWN")
                weight = EDGE_WEIGHTS.get(e_type, 1.0)
            
            weights.append(float(weight))
            
    if not src_indices:
        # Self-loops if no edges (GAT requires edge_index)
        edge_index = torch.zeros((2, 0), dtype=torch.long)
        edge_attr = torch.zeros((0, 1), dtype=torch.float)
    else:
        edge_index = torch.tensor([src_indices, dst_indices], dtype=torch.long)
        edge_attr = torch.tensor(weights, dtype=torch.float).view(-1, 1)

    # 3. Inference
    try:
        models["gat_model"].eval()
        with torch.no_grad():
            # 1. Trích xuất đặc trưng bằng GAT -> [N, 16]
            embeddings, (attn_edge_index, attn_weights) = models["gat_model"](x, edge_index, edge_attr)
            target_emb = embeddings[target_idx].cpu().numpy().reshape(1, -1)
            
            # 2. Map Attention Weights to Wallet IDs
            idx_to_node = {i: n_id for n_id, i in node_to_idx.items()}
            attn_edge_index_np = attn_edge_index.cpu().numpy()
            attn_weights_np = attn_weights.cpu().numpy()

            attention_map = {}
            for i in range(attn_edge_index_np.shape[1]):
                u_idx = attn_edge_index_np[0, i]
                v_idx = attn_edge_index_np[1, i]
                # Each GAT layer might have multiple heads; we take the first head's weight if needed
                # or the average. Since we used concat=False in the final layer, attn_weights is [E, 1]
                weight_val = float(attn_weights_np[i][0]) if len(attn_weights_np[i]) > 0 else 0.0
                attention_map[(idx_to_node[u_idx], idx_to_node[v_idx])] = weight_val

            # 3. Chuẩn hóa Embedding cho ML
            if models.get("embedding_scaler"):
                scaled_emb = models["embedding_scaler"].transform(target_emb)
            else:
                scaled_emb = target_emb
                
            # 4. Phân loại bằng Random Forest
            rf_probs = models["rf_model"].predict_proba(scaled_emb)[0]
            rf_pred_class = int(models["rf_model"].predict(scaled_emb)[0])
            
            # Predict Label and Probabilities Dictionary
            predict_label = LABEL_MAP.get(rf_pred_class, "UNKNOWN")
            predict_proba = {
                "BENIGN": float(rf_probs[0]),
                "LOW_RISK": float(rf_probs[1]) if len(rf_probs) > 1 else 0.0,
                "HIGH_RISK": float(rf_probs[2]) if len(rf_probs) > 2 else 0.0,
                "MALICIOUS": float(rf_probs[3]) if len(rf_probs) > 3 else 0.0
            }
    except Exception as e:
        logger.exception(f"Inference pipeline failed: {e}")
        return None

    # 4. Reasoning & Edge Attention Assignment
    # Scan direct connections of the target node for risky patterns
    risk_edges = []
    for u, v, data in subgraph.edges(data=True):
        # Inject GAT attention into the subgraph edge so it's serialized later
        gat_attention = attention_map.get((u, v), 0.0)
        # NetworkX MultiDiGraph stores data in a dict inside the third element of the edge tuple if using data=True
        # and we can access the actual edge data to modify it
        subgraph[u][v][0]['gat_attention'] = gat_attention
        
        if u == target_id or v == target_id:
            e_type = data.get("type", "")
            if e_type in ["CO-OWNER", "SIM_BIO", "SAME_AVATAR", "FUZZY_HANDLE"]:
                risk_edges.append(e_type)
    
    # Use confidence (highest prob) for reasoning display
    confidence = float(rf_probs[rf_pred_class])
    reasoning = generate_reasoning(rf_pred_class, risk_edges, confidence)
    
    return {
        "predict_label": predict_label,
        "predict_proba": predict_proba,
        "reasoning": reasoning
    }

def generate_reasoning(pred_class: int, risk_edges: list, sybil_prob: float) -> list:
    """
    Generate a human-readable explanation for the AI's decision as a list of points.
    """
    edge_counts = Counter(risk_edges)
    reasons = []
    
    if pred_class >= 2:
        reasons.append(f"AI model detected strong Sybil-like behavior (Confidence: {sybil_prob*100:.1f}%).")
    elif pred_class == 1:
        reasons.append(f"AI model identified minor suspicious patterns (Confidence: {sybil_prob*100:.1f}%).")
    
    if edge_counts:
        edge_details = ", ".join([f"{count}x {etype}" for etype, count in edge_counts.items()])
        reasons.append(f"Risk-associated connections: {edge_details}.")
        
    if not reasons:
        if pred_class == 0:
            return ["No significant Sybil patterns detected. Account behavior appears consistent with organic users."]
        else:
            return ["Account shows some unusual activity, but no definitive Sybil indicators were found."]
            
    return reasons
