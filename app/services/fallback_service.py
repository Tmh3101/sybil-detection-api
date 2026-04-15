import os
import json
import asyncio
import logging
import ast
import pandas as pd
import torch
import difflib
import math
from datetime import datetime
from typing import Any, Dict, Optional, Tuple
from google.cloud import bigquery
from google.oauth2 import service_account

logger = logging.getLogger(__name__)

BASE_WEIGHTS = {
    # Tầng Follow
    "FOLLOW": 1.0,
    # Tầng Interact
    "UPVOTE": 1.0,
    "REACTION": 1.0,
    "COMMENT": 2.0,
    "QUOTE": 2.0,
    "MIRROR": 3.0,
    "COLLECT": 4.0,
    "TIP": 4.0,
    # Tầng Co-Owner (undirected)
    "CO-OWNER": 10.0,
    # Tầng Similarity (undirected)
    "SIMILARITY": 5.0,
    "FUZZY_HANDLE": 5.0,
    "SIM_BIO": 5.0,
    "CLOSE_CREATION_TIME": 5.0,
}

# REV edges: chiều ngược của directed layers, weight = base * 0.5
REV_WEIGHTS = {
    k + "_REV": v * 0.5
    for k, v in BASE_WEIGHTS.items()
    if k
    in {"FOLLOW", "UPVOTE", "REACTION", "COMMENT", "QUOTE", "MIRROR", "COLLECT", "TIP"}
}

EDGE_WEIGHTS = {**BASE_WEIGHTS, **REV_WEIGHTS}

DIRECTED_EDGE_TYPES = {
    "FOLLOW",
    "UPVOTE",
    "REACTION",
    "COMMENT",
    "QUOTE",
    "MIRROR",
    "COLLECT",
    "TIP",
}

INVALID_WALLET_VALUES = {"", "unknown", "none", "nan", "null", "n/a"}


def compute_log_weight(edge_type: str, n_interactions: int = 1) -> float:
    """W_final = W_base * (1 + log10(N))"""
    base = BASE_WEIGHTS.get(edge_type, 1.0)
    return base * (1 + math.log10(max(1, n_interactions)))


# Global variable for the NLP model (Singleton)
_sentence_model = None


def get_sentence_model():
    global _sentence_model
    if _sentence_model is None:
        try:
            from sentence_transformers import SentenceTransformer

            logger.info("Loading SentenceTransformer model 'all-MiniLM-L6-v2'...")
            _sentence_model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
            logger.info("Model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load SentenceTransformer: {e}")
            _sentence_model = False  # Mark as failed so we don't retry endlessly
    return _sentence_model if _sentence_model is not False else None


def normalize_wallet(value) -> str | None:
    if value is None:
        return None
    wallet = str(value).strip().lower()
    return wallet if wallet not in INVALID_WALLET_VALUES else None


def normalize_handle(value) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def safe_to_datetime(value):
    if value is None:
        return None
    try:
        return value if isinstance(value, datetime) else pd.to_datetime(value)
    except Exception:
        return None


def to_1d_float_tensor(embedding):
    if embedding is None:
        return None
    try:
        if isinstance(embedding, torch.Tensor):
            tensor = embedding.detach().float().cpu()
        else:
            tensor = torch.tensor(embedding, dtype=torch.float32)
        if tensor.ndim > 1:
            tensor = tensor.view(-1)
        return tensor if tensor.numel() > 0 else None
    except Exception:
        return None


def parse_metadata(meta_str):
    """
    Safely parse metadata string to extract picture_url.
    """
    if not meta_str or pd.isna(meta_str):
        return ""
    try:
        # Using ast.literal_eval for safe parsing of dictionary-like strings
        meta = ast.literal_eval(str(meta_str))
        # Handle different metadata structures seen in Module 1
        lens_meta = meta.get("lens", {})
        return lens_meta.get("picture", "") or ""
    except Exception as e:
        logger.debug(f"Failed to parse metadata: {e}")
        return ""


def parse_bio(meta_str):
    """
    Safely parse metadata string to extract bio.
    """
    if not meta_str or pd.isna(meta_str):
        return ""
    try:
        meta = ast.literal_eval(str(meta_str))
        lens_meta = meta.get("lens", {})
        return lens_meta.get("bio", "") or ""
    except Exception as e:
        logger.debug(f"Failed to parse bio: {e}")
        return ""


def get_bq_client():
    """
    Initialize BigQuery client from a service account key file or environment variable.
    Prioritizes:
    1. Local file '.creds/service-account-key.json'
    2. Environment variable 'GOOGLE_APPLICATION_CREDENTIALS' (file path or JSON content)
    """
    local_key = ".creds/service-account-key.json"
    if os.path.exists(local_key):
        logger.info(f"Using local credentials file: {local_key}")
        return bigquery.Client.from_service_account_json(local_key, location="US")

    creds_env = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds_env:
        logger.warning(
            "Neither service-account-key.json nor GOOGLE_APPLICATION_CREDENTIALS found. Using default credentials."
        )
        return bigquery.Client(location="US")

    # Check if GOOGLE_APPLICATION_CREDENTIALS is a JSON string or a file path
    if creds_env.strip().startswith("{"):
        try:
            creds_dict = json.loads(creds_env)
            credentials = service_account.Credentials.from_service_account_info(
                creds_dict
            )
            return bigquery.Client(
                credentials=credentials,
                project=creds_dict.get("project_id"),
                location="US",
            )
        except json.JSONDecodeError:
            logger.error(
                "GOOGLE_APPLICATION_CREDENTIALS looks like JSON but failed to parse."
            )
            return bigquery.Client(location="US")
    else:
        # Assume it's a file path
        if os.path.exists(creds_env):
            return bigquery.Client.from_service_account_json(creds_env, location="US")
        else:
            logger.error(f"Credentials file not found at: {creds_env}")
            return bigquery.Client(location="US")


async def fetch_and_embed_node(
    app, profile_id: str
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Fetch a single node and its related edges from BigQuery, then embed into app.state.graph.
    Only edges connecting to existing nodes in the graph are added.
    """
    profile_id_clean = profile_id.lower()
    debug_stats: Dict[str, Any] = {
        "fallback_triggered": True,
        "target_profile_id": profile_id_clean,
    }

    def sync_fallback():
        client = get_bq_client()

        # 1. Query Node Metadata with raw metadata parsing
        query_node = f"""
        SELECT
            `lens-protocol-mainnet.app.FORMAT_HEX`(meta.account) as profile_id,
            ANY_VALUE(meta.metadata) as raw_metadata,
            ANY_VALUE(meta.name) as display_name,
            ANY_VALUE(`lens-protocol-mainnet.app.FORMAT_HEX`(ksw.owned_by)) as owned_by,
            ANY_VALUE(meta.created_on) as created_on,
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
        WHERE `lens-protocol-mainnet.app.FORMAT_HEX`(meta.account) = '{profile_id_clean}'
        GROUP BY 1
        """

        df_node = client.query(query_node).to_dataframe()
        if df_node.empty:
            logger.info(f"Profile {profile_id} not found on BigQuery.")
            return None, None

        row = df_node.iloc[0]
        node_data = {
            "profile_id": profile_id_clean,
            "handle": str(row.get("handle", "unknown")),
            "display_name": str(row.get("display_name", "")),
            "picture_url": parse_metadata(row.get("raw_metadata")),
            "owned_by": str(row.get("owned_by", "")).strip().lower(),
            "bio": parse_bio(row.get("raw_metadata")),
            "created_on": row["created_on"],
            "trust_score": (
                float(row.get("trust_score", 0.0))
                if pd.notna(row.get("trust_score"))
                else 0.0
            ),
            "total_posts": (
                int(row.get("total_posts", 0))
                if pd.notna(row.get("total_posts"))
                else 0
            ),
            "total_comments": (
                int(row.get("total_comments", 0))
                if pd.notna(row.get("total_comments"))
                else 0
            ),
            "total_reposts": (
                int(row.get("total_reposts", 0))
                if pd.notna(row.get("total_reposts"))
                else 0
            ),
            "total_collects": (
                int(row.get("total_collects", 0))
                if pd.notna(row.get("total_collects"))
                else 0
            ),
            "total_tips": (
                int(row.get("total_tips", 0)) if pd.notna(row.get("total_tips")) else 0
            ),
            "total_quotes": (
                int(row.get("total_quotes", 0))
                if pd.notna(row.get("total_quotes"))
                else 0
            ),
            "total_reacted": (
                int(row.get("total_reacted", 0))
                if pd.notna(row.get("total_reacted"))
                else 0
            ),
            "total_reactions": (
                int(row.get("total_reactions", 0))
                if pd.notna(row.get("total_reactions"))
                else 0
            ),
            "total_followers": (
                int(row.get("total_followers", 0))
                if pd.notna(row.get("total_followers"))
                else 0
            ),
            "total_following": (
                int(row.get("total_following", 0))
                if pd.notna(row.get("total_following"))
                else 0
            ),
        }

        logger.info(f"--- [NODE VERIFICATION: {profile_id}] ---")
        logger.info(
            f"1. Info: Handle='{node_data.get('handle')}', OwnedBy='{node_data.get('owned_by')}', HasAvatar={'Yes' if node_data.get('picture_url') else 'No'}"
        )
        logger.info(node_data)
        logger.info(
            f"2. Stats: TrustScore={node_data.get('trust_score')}, Posts={node_data.get('total_posts')}, Followers={node_data.get('total_followers')}, Following={node_data.get('total_following')}"
        )

        # 2. Query Edges (Follow & Interact)
        query_edges = f"""
        -- 1. Tầng FOLLOW
        SELECT
            `lens-protocol-mainnet.app.FORMAT_HEX`(account_follower) as source,
            `lens-protocol-mainnet.app.FORMAT_HEX`(account_following) as target,
            'FOLLOW' as edge_type
        FROM `lens-protocol-mainnet.account.follower`
        WHERE `lens-protocol-mainnet.app.FORMAT_HEX`(account_follower) = '{profile_id_clean}'
           OR `lens-protocol-mainnet.app.FORMAT_HEX`(account_following) = '{profile_id_clean}'

        UNION ALL

        -- 2. Tầng INTERACT (Comment, Quote)
        SELECT
            `lens-protocol-mainnet.app.FORMAT_HEX`(p.account) as source,
            `lens-protocol-mainnet.app.FORMAT_HEX`(parent.account) as target,
            CASE
                WHEN p.parent_post IS NOT NULL THEN 'COMMENT'
                ELSE 'QUOTE'
            END as edge_type
        FROM `lens-protocol-mainnet.post.record` p
        JOIN `lens-protocol-mainnet.post.record` parent
          ON (p.parent_post = parent.id OR p.quoted_post = parent.id)
        WHERE (`lens-protocol-mainnet.app.FORMAT_HEX`(p.account) = '{profile_id_clean}'
           OR `lens-protocol-mainnet.app.FORMAT_HEX`(parent.account) = '{profile_id_clean}')
           AND p.account != parent.account

        UNION ALL

        -- 3. Tầng REACTION (Upvote/Downvote)
        SELECT
            `lens-protocol-mainnet.app.FORMAT_HEX`(r.account) as source,
            `lens-protocol-mainnet.app.FORMAT_HEX`(p.account) as target,
            r.type as edge_type
        FROM `lens-protocol-mainnet.post.reaction` r
        JOIN `lens-protocol-mainnet.post.record` p ON r.post = p.id
        WHERE (`lens-protocol-mainnet.app.FORMAT_HEX`(r.account) = '{profile_id_clean}'
           OR `lens-protocol-mainnet.app.FORMAT_HEX`(p.account) = '{profile_id_clean}')

        UNION ALL

        -- 4. Tầng COLLECT
        SELECT
            `lens-protocol-mainnet.app.FORMAT_HEX`(a.account) as source,
            `lens-protocol-mainnet.app.FORMAT_HEX`(p.account) as target,
            'COLLECT' as edge_type
        FROM `lens-protocol-mainnet.post.action_executed` a
        JOIN `lens-protocol-mainnet.post.record` p ON a.post_id = p.id
        WHERE (`lens-protocol-mainnet.app.FORMAT_HEX`(a.account) = '{profile_id_clean}'
           OR `lens-protocol-mainnet.app.FORMAT_HEX`(p.account) = '{profile_id_clean}')
           AND a.type = 'SimpleCollectAction'
        """

        df_edges = client.query(query_edges).to_dataframe()
        return node_data, df_edges

    try:
        node_data, df_edges = await asyncio.to_thread(sync_fallback)

        if not node_data:
            debug_stats["result"] = "profile_not_found"
            return False, debug_stats

        G = app.state.graph
        graph_nodes_before = G.number_of_nodes()
        debug_stats["graph_nodes_before"] = graph_nodes_before
        logger.info(f"========== BẮT ĐẦU FALLBACK PIPELINE CHO {profile_id} ==========")
        logger.info(f"[GRAPH STATE] Hiện có {graph_nodes_before} nodes trong RAM.")

        # Add Node
        G.add_node(
            node_data["profile_id"],
            handle=node_data["handle"],
            display_name=node_data["display_name"],
            picture_url=node_data["picture_url"],
            owned_by=node_data["owned_by"],
            bio=node_data["bio"],
            created_on=node_data["created_on"],
            trust_score=node_data["trust_score"],
            total_posts=node_data["total_posts"],
            total_comments=node_data["total_comments"],
            total_reposts=node_data["total_reposts"],
            total_collects=node_data["total_collects"],
            total_tips=node_data["total_tips"],
            total_quotes=node_data["total_quotes"],
            total_reacted=node_data["total_reacted"],
            total_reactions=node_data["total_reactions"],
            total_followers=node_data["total_followers"],
            total_following=node_data["total_following"],
            is_lazy=True,
        )

        # Add Edges (Physical - Directed)
        if df_edges is not None and not df_edges.empty:
            logger.info(
                f"[BIGQUERY EDGES] Kéo về {len(df_edges)} raw edges từ BigQuery."
            )
            attached_edges = 0
            ignored_edges = 0
            for _, row in df_edges.iterrows():
                src = row["source"]
                tgt = row["target"]
                edge_type = row["edge_type"]
                weight = EDGE_WEIGHTS.get(edge_type, 1.0)

                # Check if the OTHER node exists in G
                neighbor = tgt if src == profile_id_clean else src
                if neighbor in G:
                    G.add_edge(src, tgt, edge_type=edge_type, weight=weight)
                    if edge_type in DIRECTED_EDGE_TYPES:
                        rev_type = edge_type + "_REV"
                        rev_weight = weight * 0.5
                        G.add_edge(tgt, src, edge_type=rev_type, weight=rev_weight)

                    attached_edges += 1
                else:
                    ignored_edges += 1

            logger.info(
                f"[PHYSICAL EDGES SUMMARY] Đã nối: {attached_edges} edges. Bỏ qua (ngoài RAM): {ignored_edges} edges."
            )
        else:
            attached_edges = 0
            ignored_edges = 0

        debug_stats["physical_edges"] = {
            "raw_fetched": int(len(df_edges)) if df_edges is not None else 0,
            "attached": attached_edges,
            "ignored_outside_ram": ignored_edges,
        }

        # 3. Graph Enrichment (Logical - Undirected)
        target_pid = node_data["profile_id"]
        new_wallet = normalize_wallet(node_data.get("owned_by"))
        new_handle = normalize_handle(node_data.get("handle"))
        new_bio = str(node_data.get("bio") or "")
        new_created_on = safe_to_datetime(node_data.get("created_on"))

        # 3.1 CO-OWNER edges
        co_owner_candidates = 0
        co_owner_added = 0
        co_owner_samples = []
        if new_wallet:
            for n_id, attrs in G.nodes(data=True):
                if n_id == target_pid:
                    continue
                if normalize_wallet(attrs.get("owned_by")) != new_wallet:
                    continue

                co_owner_candidates += 1
                G.add_edge(
                    target_pid,
                    n_id,
                    edge_type="CO-OWNER",
                    weight=EDGE_WEIGHTS["CO-OWNER"],
                    shared_wallet=new_wallet,
                )
                G.add_edge(
                    n_id,
                    target_pid,
                    edge_type="CO-OWNER",
                    weight=EDGE_WEIGHTS["CO-OWNER"],
                    shared_wallet=new_wallet,
                )
                co_owner_added += 1
                if len(co_owner_samples) < 5:
                    co_owner_samples.append(
                        {"neighbor_id": n_id, "shared_wallet": new_wallet}
                    )
        else:
            logger.info(
                f"[CO-OWNER] Skip for {target_pid}: owned_by is empty/invalid ({node_data.get('owned_by')})."
            )
        logger.info(
            f"[CO-OWNER SUMMARY] candidates={co_owner_candidates}, undirected_pairs_added={co_owner_added}, directed_edges_added={co_owner_added * 2}"
        )
        debug_stats["co_owner"] = {
            "wallet_valid": bool(new_wallet),
            "wallet": new_wallet,
            "candidates": co_owner_candidates,
            "undirected_pairs_added": co_owner_added,
            "samples": co_owner_samples,
        }

        # 3.2 SIMILARITY edges (canonical SIMILARITY type, 2/3 rule)
        new_bio_tensor = None
        if len(new_bio.strip()) > 5:
            model = get_sentence_model()
            if model:
                try:
                    logger.info(
                        f"[SIM_BIO] Encoding bio for {target_pid}: '{new_bio[:50]}...'"
                    )
                    new_bio_tensor = to_1d_float_tensor(
                        model.encode([new_bio], convert_to_tensor=True)[0]
                    )
                except Exception as e:
                    logger.error(f"Lỗi khi encode bio cho {profile_id}: {e}")

        # Persist normalized tensor for future fallback calls
        G.nodes[target_pid]["bio_embedding"] = new_bio_tensor

        sim_bio_scores = {}
        neighbors_with_embedding = 0
        if new_bio_tensor is not None:
            valid_neighbors = []
            existing_embs = []
            for n_id, attrs in G.nodes(data=True):
                if n_id == target_pid:
                    continue
                cached_emb = to_1d_float_tensor(attrs.get("bio_embedding"))
                if cached_emb is not None:
                    valid_neighbors.append(n_id)
                    existing_embs.append(cached_emb)
            neighbors_with_embedding = len(valid_neighbors)

            if valid_neighbors:
                try:
                    existing_matrix = torch.stack(existing_embs)
                    cosine_scores = torch.nn.functional.cosine_similarity(
                        existing_matrix, new_bio_tensor.unsqueeze(0), dim=1
                    )
                    sim_bio_scores = {
                        valid_neighbors[idx]: float(score.item())
                        for idx, score in enumerate(cosine_scores)
                    }
                except Exception as e:
                    logger.warning(
                        f"[SIM_BIO] Failed to compute batched cosine scores for {target_pid}: {e}"
                    )

        similarity_candidates = 0
        similarity_added = 0
        similarity_skipped_by_rule = 0
        similarity_samples = []
        for n_id, attrs in G.nodes(data=True):
            if n_id == target_pid:
                continue

            similarity_candidates += 1
            violations = []
            detail = {}

            sim_bio = sim_bio_scores.get(n_id)
            if sim_bio is not None and sim_bio >= 0.8:
                violations.append(f"SIM_BIO ({sim_bio:.2f})")
                detail["SIM_BIO"] = round(sim_bio, 4)

            n_handle = normalize_handle(attrs.get("handle"))
            if len(new_handle) > 3 and len(n_handle) > 3:
                ratio = difflib.SequenceMatcher(None, new_handle, n_handle).ratio()
                if ratio >= 0.85:
                    violations.append(f"FUZZY_HANDLE ({ratio:.2f})")
                    detail["FUZZY_HANDLE"] = round(ratio, 4)

            n_created_on = safe_to_datetime(attrs.get("created_on"))
            if new_created_on is not None and n_created_on is not None:
                diff_sec = abs((new_created_on - n_created_on).total_seconds())
                if diff_sec <= 3600:
                    violations.append("CLOSE_CREATION_TIME")
                    detail["CLOSE_CREATION_TIME_SECONDS"] = float(diff_sec)

            if len(violations) < 2:
                similarity_skipped_by_rule += 1
                if len(similarity_samples) < 5:
                    similarity_samples.append(
                        {
                            "neighbor_id": n_id,
                            "decision": "skipped_by_2of3",
                            "signals": violations,
                            "signal_count": len(violations),
                            "detail": detail,
                        }
                    )
                continue

            sim_weight = EDGE_WEIGHTS["SIMILARITY"]
            metadata = {"total_flags": len(violations), "detail": detail}
            G.add_edge(
                target_pid,
                n_id,
                edge_type="SIMILARITY",
                weight=sim_weight,
                violations=violations,
                metadata=metadata,
            )
            G.add_edge(
                n_id,
                target_pid,
                edge_type="SIMILARITY",
                weight=sim_weight,
                violations=violations,
                metadata=metadata,
            )
            similarity_added += 1
            if len(similarity_samples) < 5:
                similarity_samples.append(
                    {
                        "neighbor_id": n_id,
                        "decision": "added",
                        "signals": violations,
                        "signal_count": len(violations),
                        "detail": detail,
                    }
                )
            logger.info(
                f"   -> [SIMILARITY 2/3] Nối với {n_id} ({', '.join(violations)})"
            )

        logger.info(
            "[SIMILARITY SUMMARY] "
            f"candidates={similarity_candidates}, "
            f"undirected_pairs_added={similarity_added}, "
            f"skipped_by_2of3={similarity_skipped_by_rule}, "
            f"directed_edges_added={similarity_added * 2}"
        )
        debug_stats["similarity"] = {
            "candidates": similarity_candidates,
            "neighbors_with_embedding": neighbors_with_embedding,
            "undirected_pairs_added": similarity_added,
            "skipped_by_2of3": similarity_skipped_by_rule,
            "samples": similarity_samples,
        }

        # --- [EDGES VERIFICATION] ---
        try:
            out_edge_counts = {}
            in_edge_counts = {}

            for _, _, data in G.out_edges(target_pid, data=True):
                e_type = data.get("edge_type", "UNKNOWN")
                out_edge_counts[e_type] = out_edge_counts.get(e_type, 0) + 1

            for _, _, data in G.in_edges(target_pid, data=True):
                e_type = data.get("edge_type", "UNKNOWN")
                in_edge_counts[e_type] = in_edge_counts.get(e_type, 0) + 1

            edge_counts = {}
            for e_type, count in out_edge_counts.items():
                edge_counts[e_type] = edge_counts.get(e_type, 0) + count
            for e_type, count in in_edge_counts.items():
                edge_counts[e_type] = edge_counts.get(e_type, 0) + count

            # Ánh xạ Edge Type sang Layer
            layers = {
                "FOLLOW": "Follow Layer (Directed)",
                "UPVOTE": "Interact Layer (Directed)",
                "REACTION": "Interact Layer (Directed)",
                "COMMENT": "Interact Layer (Directed)",
                "QUOTE": "Interact Layer (Directed)",
                "MIRROR": "Interact Layer (Directed)",
                "COLLECT": "Interact Layer (Directed)",
                "CO-OWNER": "Co-Owner Layer (Undirected)",
                "SIMILARITY": "Similarity Layer (Undirected)",
                "FUZZY_HANDLE": "Similarity Layer (Undirected)",
                "SIM_BIO": "Similarity Layer (Undirected)",
                "CLOSE_CREATION_TIME": "Similarity Layer (Undirected)",
            }

            # Tự động map các cạnh _REV vào đúng Layer của cạnh gốc
            for e_type in list(layers.keys()):
                if e_type in DIRECTED_EDGE_TYPES:
                    layers[e_type + "_REV"] = layers[e_type]

            layer_counts = {}
            for e_type, count in edge_counts.items():
                layer = layers.get(e_type, "Unknown Layer")
                layer_counts[layer] = layer_counts.get(layer, 0) + count

            logger.info(f"--- [EDGES VERIFICATION: {profile_id}] ---")
            logger.info(
                f"Tổng số Edges kết nối: outgoing={sum(out_edge_counts.values())}, incoming={sum(in_edge_counts.values())}, combined={sum(edge_counts.values())}"
            )
            logger.info("Thống kê theo Tầng (Layers):")
            for layer, count in layer_counts.items():
                logger.info(f"  - {layer}: {count} edges")

            logger.info("Chi tiết theo Loại (Types):")
            for e_type, count in edge_counts.items():
                weight = EDGE_WEIGHTS.get(e_type, 1.0)
                logger.info(f"  - [{e_type}] (Weight: {weight}): {count} edges")

        except Exception as e:
            logger.error(f"Lỗi khi thống kê Edges: {e}")

        debug_stats["graph_nodes_after"] = G.number_of_nodes()
        debug_stats["result"] = "embedded"
        logger.info("========== KẾT THÚC FALLBACK PIPELINE ==========")
        return True, debug_stats

    except Exception as e:
        logger.exception(f"Error in Fallback Pipeline for {profile_id}: {e}")
        debug_stats["result"] = "error"
        debug_stats["error"] = str(e)
        return False, debug_stats
