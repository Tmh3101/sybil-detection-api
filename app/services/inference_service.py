"""
inference_service.py — Fixed GAT attention extraction
Root cause fix: use attn_edge_index from GATConv (which includes self-loops and re-indexing)
instead of the original edge_index for mapping attention weights to node IDs.
"""
import torch
import torch.nn.functional as F
import numpy as np
import pandas as pd
from datetime import datetime, timezone
import logging
import networkx as nx
from collections import Counter
from typing import Optional

from app.services.fallback_service import EDGE_WEIGHTS

logger = logging.getLogger(__name__)

LABEL_MAP = {0: "BENIGN", 1: "LOW_RISK", 2: "HIGH_RISK", 3: "MALICIOUS"}


async def evaluate_subgraph(models: dict, subgraph: nx.MultiDiGraph, target_id: str):
    """
    Hybrid AI inference on ego-graph.

    Returns attention_weights for ALL meaningful edges in subgraph.

    Key fix: PyG GATConv.return_attention_weights returns attn_edge_index which
    differs from the original edge_index due to:
    - Internal self-loop addition (add_self_loops=True by default)
    - Edge re-indexing after neighborhood aggregation

    We MUST iterate over attn_edge_index (not original edge_index) when
    mapping attention values back to node IDs. This is why only 1 edge
    was showing attention — all others had index mismatches.
    """
    if not models or not models.get("gat_model") or not models.get("rf_model"):
        logger.error("Inference models not loaded properly.")
        return None

    node_list = list(subgraph.nodes())
    try:
        target_idx = node_list.index(target_id)
    except ValueError:
        logger.error(f"Target node {target_id} not found in subgraph.")
        return None

    N = len(node_list)
    node_to_idx = {n_id: i for i, n_id in enumerate(node_list)}
    idx_to_node = {i: n_id for n_id, i in node_to_idx.items()}
    now = datetime.now(timezone.utc)

    # ── A: Numeric features (Nx12) ──
    numeric_data = []
    for n_id in node_list:
        attrs = subgraph.nodes[n_id]
        created_on = attrs.get("created_on")
        days_active = 0
        if created_on:
            try:
                created_dt = pd.to_datetime(created_on)
                if created_dt.tzinfo is None:
                    created_dt = created_dt.replace(tzinfo=timezone.utc)
                days_active = max(0, (now - created_dt).days)
            except Exception:
                pass
        numeric_data.append([
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
            float(days_active),
        ])

    numeric_np = np.array(numeric_data, dtype=np.float32)
    if models.get("feature_scaler"):
        try:
            numeric_np = models["feature_scaler"].transform(numeric_np)
        except Exception as e:
            logger.warning(f"Feature scaler failed: {e}")
    numeric_tensor = torch.tensor(numeric_np, dtype=torch.float)

    # ── B: Text embeddings (Nx384) ──
    texts = []
    for n_id in node_list:
        attrs = subgraph.nodes[n_id]
        handle = attrs.get("handle") or "unknown"
        display_name = attrs.get("display_name") or handle
        bio = attrs.get("bio") or ""
        texts.append(f"Handle: {handle}. Name: {display_name}. Bio: {bio}")

    if models.get("nlp_model"):
        try:
            text_emb = models["nlp_model"].encode(texts, convert_to_tensor=True)
            text_tensor = text_emb.to(torch.float32)
        except Exception as e:
            logger.warning(f"NLP encoding failed: {e}")
            text_tensor = torch.zeros((N, 384), dtype=torch.float)
    else:
        text_tensor = torch.zeros((N, 384), dtype=torch.float)

    # ── C: Node features [N, 396] ──
    x = torch.cat([numeric_tensor, text_tensor], dim=1)

    # ── D: Edge tensors ──
    # Build edge_type lookup: (src_id, tgt_id) -> edge_type
    # For undirected edges that appear in both directions, we look up both orderings.
    edge_type_lookup: dict[tuple[str, str], str] = {}
    src_indices, dst_indices, weights = [], [], []

    for u, v, edata in subgraph.edges(data=True):
        if u in node_to_idx and v in node_to_idx:
            si = node_to_idx[u]
            ti = node_to_idx[v]
            src_indices.append(si)
            dst_indices.append(ti)
            etype = edata.get("type", "UNKNOWN")
            w = edata.get("weight") or EDGE_WEIGHTS.get(etype, 1.0)
            weights.append(float(w))
            edge_type_lookup[(u, v)] = etype
            # Also register reverse for undirected lookup fallback
            if (v, u) not in edge_type_lookup:
                edge_type_lookup[(v, u)] = etype

    if not src_indices:
        edge_index = torch.zeros((2, 0), dtype=torch.long)
        edge_attr = torch.zeros((0, 1), dtype=torch.float)
    else:
        edge_index = torch.tensor([src_indices, dst_indices], dtype=torch.long)
        edge_attr = torch.tensor(weights, dtype=torch.float).view(-1, 1)

    # ── E: Inference + Attention Extraction ──
    attention_weights_all = []

    try:
        gat_model = models["gat_model"]
        gat_model.eval()

        with torch.no_grad():
            # ── Layer 1 forward ──
            h1 = gat_model.conv1(x, edge_index, edge_attr=edge_attr)
            h1 = F.elu(h1)

            # ── Layer 2 forward WITH attention weights ──
            # CRITICAL: attn_edge_index is NOT the same as edge_index.
            # GATConv adds self-loops internally, so attn_edge_index may have
            # more entries. We iterate over attn_edge_index to get correct mapping.
            try:
                h2_out, (attn_edge_index, attn_weights) = gat_model.conv2(
                    h1,
                    edge_index,
                    edge_attr=edge_attr,
                    return_attention_weights=True,
                )
                # attn_weights: [E_attn, num_heads] — Layer 2 has 1 head
                # attn_edge_index: [2, E_attn] — may include self-loops
                attn_vals = attn_weights.squeeze(-1).cpu().numpy()   # [E_attn]
                attn_src = attn_edge_index[0].cpu().numpy()          # [E_attn]
                attn_tgt = attn_edge_index[1].cpu().numpy()          # [E_attn]

                # ── FIX: Iterate attn_edge_index, NOT original edge_index ──
                for i in range(len(attn_vals)):
                    src_idx = int(attn_src[i])
                    tgt_idx = int(attn_tgt[i])

                    # Skip self-loops (GATConv adds these internally)
                    if src_idx == tgt_idx:
                        continue

                    # Skip indices outside our node range (shouldn't happen, but safe)
                    if src_idx >= N or tgt_idx >= N:
                        continue

                    src_id = idx_to_node[src_idx]
                    tgt_id = idx_to_node[tgt_idx]
                    attn_val = float(attn_vals[i])

                    # Lookup original edge type
                    etype = edge_type_lookup.get((src_id, tgt_id),
                             edge_type_lookup.get((tgt_id, src_id), "UNKNOWN"))

                    # Hop classification:
                    # hop=1: edge directly connects to target
                    # hop=2: edge between two non-target neighbors
                    hop = 1 if (src_id == target_id or tgt_id == target_id) else 2

                    attention_weights_all.append({
                        "source": src_id,
                        "target": tgt_id,
                        "attention": round(attn_val, 6),
                        "edge_type": etype,
                        "hop": hop,
                    })

                logger.info(
                    f"[GAT] Extracted {len(attention_weights_all)} attention weights "
                    f"(attn_edge_index size={len(attn_vals)}, skipped self-loops)"
                )

            except Exception as attn_err:
                # Fallback: normalized edge weights as proxy attention
                logger.warning(
                    f"return_attention_weights failed: {attn_err}. "
                    "Using normalized edge weights as proxy."
                )
                if weights:
                    w_max = max(weights) or 1.0
                    for ei, (si, ti) in enumerate(zip(src_indices, dst_indices)):
                        if si == ti:
                            continue
                        src_id = idx_to_node.get(si, "")
                        tgt_id = idx_to_node.get(ti, "")
                        if src_id and tgt_id:
                            etype = edge_type_lookup.get((src_id, tgt_id), "UNKNOWN")
                            hop = 1 if (src_id == target_id or tgt_id == target_id) else 2
                            attention_weights_all.append({
                                "source": src_id,
                                "target": tgt_id,
                                "attention": round(weights[ei] / w_max, 6),
                                "edge_type": etype,
                                "hop": hop,
                            })

            # ── Standard forward for classification ──
            embeddings = gat_model(x, edge_index, edge_attr)
            target_emb = embeddings[target_idx].cpu().numpy().reshape(1, -1)

            if models.get("embedding_scaler"):
                scaled_emb = models["embedding_scaler"].transform(target_emb)
            else:
                scaled_emb = target_emb

            rf_probs = models["rf_model"].predict_proba(scaled_emb)[0]
            rf_pred_class = int(models["rf_model"].predict(scaled_emb)[0])

            predict_label = LABEL_MAP.get(rf_pred_class, "UNKNOWN")
            predict_proba = {
                "BENIGN":    float(rf_probs[0]),
                "LOW_RISK":  float(rf_probs[1]) if len(rf_probs) > 1 else 0.0,
                "HIGH_RISK": float(rf_probs[2]) if len(rf_probs) > 2 else 0.0,
                "MALICIOUS": float(rf_probs[3]) if len(rf_probs) > 3 else 0.0,
            }

    except Exception as e:
        logger.exception(f"Inference pipeline failed: {e}")
        return None

    # ── F: Reasoning ──
    risk_edges = [
        edata.get("type", "")
        for u, v, edata in subgraph.edges(data=True)
        if (u == target_id or v == target_id)
        and edata.get("type", "") in ("CO-OWNER", "SIM_BIO", "SAME_AVATAR", "FUZZY_HANDLE")
    ]
    confidence = float(rf_probs[rf_pred_class])
    reasoning = _generate_reasoning(rf_pred_class, risk_edges, confidence)

    return {
        "predict_label": predict_label,
        "predict_proba": predict_proba,
        "reasoning": reasoning,
        "attention_weights": attention_weights_all,
    }


def _generate_reasoning(pred_class: int, risk_edges: list, sybil_prob: float) -> list:
    edge_counts = Counter(risk_edges)
    reasons = []
    if pred_class >= 2:
        reasons.append(
            f"AI model detected strong Sybil-like behavior (Confidence: {sybil_prob*100:.1f}%)."
        )
    elif pred_class == 1:
        reasons.append(
            f"AI model identified minor suspicious patterns (Confidence: {sybil_prob*100:.1f}%)."
        )
    if edge_counts:
        details = ", ".join(f"{cnt}x {et}" for et, cnt in edge_counts.items())
        reasons.append(f"Risk-associated connections: {details}.")
    if not reasons:
        return (
            ["No significant Sybil patterns detected."]
            if pred_class == 0
            else ["Account shows unusual activity but no definitive Sybil indicators."]
        )
    return reasons