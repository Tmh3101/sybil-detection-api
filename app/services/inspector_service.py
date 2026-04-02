import os
import asyncio
import logging
import torch
import pandas as pd
import networkx as nx

logger = logging.getLogger(__name__)


async def load_reference_graph(pt_path: str, meta_path: str) -> nx.MultiDiGraph:
    """
    Load the PyTorch Geometric graph and CSV metadata into a NetworkX MultiDiGraph.

    This function:
    1. Loads the .pt file (PyG Data object) and the .csv metadata file.
    2. Validates that the number of nodes matches.
    3. Maps node indices to profile IDs using the metadata.
    4. Populates a NetworkX MultiDiGraph with nodes (and their attributes) and edges.
    """
    if not os.path.exists(pt_path) or not os.path.exists(meta_path):
        logger.warning(
            f"Data files not found: {pt_path} or {meta_path}. Returning empty graph."
        )
        return nx.MultiDiGraph()

    try:
        # Resolve path for pre-computed bio embeddings
        emb_path = os.path.join(os.path.dirname(pt_path), "bio_embeddings.pt")

        # Load data in a separate thread to avoid blocking the event loop
        def sync_load():
            # Using weights_only=False because PyG Data objects are often complex pickles
            # and map_location='cpu' as instructed.
            data = torch.load(pt_path, map_location="cpu", weights_only=False)
            df_meta = pd.read_csv(meta_path)

            # Load cluster labels if available
            cluster_path = os.path.join(os.path.dirname(pt_path), "kmeans_labels.csv")
            df_clusters = None
            if os.path.exists(cluster_path):
                logger.info(f"Loading cluster labels from {cluster_path}...")
                df_clusters = pd.read_csv(cluster_path)

            # Load rule-based scoring labels if available
            rules_path = os.path.join(
                os.path.dirname(pt_path), "rule_based_scoring_labels.csv"
            )
            df_rules = None
            if os.path.exists(rules_path):
                logger.info(f"Loading rule-based scoring labels from {rules_path}...")
                df_rules = pd.read_csv(rules_path)

            bio_embs = {}
            if os.path.exists(emb_path):
                logger.info(f"Loading pre-computed bio embeddings from {emb_path}...")
                bio_embs = torch.load(emb_path, map_location="cpu", weights_only=False)
            else:
                logger.warning(
                    f"Bio embeddings file not found at {emb_path}. Proceeding without it."
                )

            return data, df_meta, bio_embs, df_clusters, df_rules

        data, df_meta, bio_embs, df_clusters, df_rules = await asyncio.to_thread(
            sync_load
        )

        # Basic validation
        num_nodes_pt = data.num_nodes if hasattr(data, "num_nodes") else data.x.size(0)
        if num_nodes_pt != len(df_meta):
            logger.error(
                f"Mismatch: num_nodes ({num_nodes_pt}) != len(df_meta) ({len(df_meta)})"
            )
            return nx.MultiDiGraph()

        G = nx.MultiDiGraph()

        # Create cluster mapping for fast lookup
        cluster_map = {}
        if df_clusters is not None:
            # Expected columns: profile_id, cluster_label
            cluster_map = df_clusters.set_index("profile_id")["cluster_label"].to_dict()

        # Create reason mapping
        reason_map = {}
        risk_map = {}
        if df_rules is not None:
            # Expected columns: profile_id, reason, risk_score
            reason_map = df_rules.set_index("profile_id")["reason"].to_dict()
            if "risk_score" in df_rules.columns:
                risk_map = df_rules.set_index("profile_id")["risk_score"].to_dict()

        # Add Nodes
        # Expected columns in metadata: profile_id, handle, picture_url, owned_by
        # Using profile_id as the node key
        logger.info(f"Adding {len(df_meta)} nodes to Backbone...")

        # Extract labels from PyG data if available (data.y)
        labels = []
        if hasattr(data, "y") and data.y is not None:
            labels = data.y.view(-1).tolist()
        else:
            # Default to BENIGN (0) if labels are missing
            labels = [0] * len(df_meta)

        for i, row in df_meta.iterrows():
            profile_id = str(row["profile_id"])
            G.add_node(
                profile_id,
                handle=row.get("handle"),
                display_name=row.get("display_name"),
                picture_url=row.get("picture_url"),
                owned_by=row.get("owned_by"),
                bio=row.get("bio", ""),
                bio_embedding=bio_embs.get(profile_id, None),
                created_on=row.get("created_on"),
                trust_score=row.get("trust_score", 0),
                total_tips=row.get("total_tips", 0),
                total_posts=row.get("total_posts", 0),
                total_quotes=row.get("total_quotes", 0),
                total_reacted=row.get("total_reacted", 0),
                total_reactions=row.get("total_reactions", 0),
                total_reposts=row.get("total_reposts", 0),
                total_collects=row.get("total_collects", 0),
                total_comments=row.get("total_comments", 0),
                total_followers=row.get("total_followers", 0),
                total_following=row.get("total_following", 0),
                label=int(labels[i]) if i < len(labels) else 0,
                cluster_id=cluster_map.get(profile_id),
                reason=reason_map.get(profile_id, ""),
                risk_score=risk_map.get(profile_id),
            )

        # Add Edges
        # edge_index is [2, num_edges]
        if hasattr(data, "edge_index"):
            logger.info(f"Adding {data.edge_index.size(1)} edges to Backbone...")
            source_indices = data.edge_index[0].tolist()
            target_indices = data.edge_index[1].tolist()

            # Safely extract and flatten weights and types
            weights_list = (
                data.edge_attr.view(-1).tolist()
                if hasattr(data, "edge_attr") and data.edge_attr is not None
                else None
            )
            types_list = (
                data.edge_type.view(-1).tolist()
                if hasattr(data, "edge_type") and data.edge_type is not None
                else None
            )

            # Reverse mapping for lookup: Integer -> String (Aligned with Colab training)
            INT_TO_EDGE_TYPE = {
                0: "FOLLOW",
                1: "COMMENT",
                2: "QUOTE",
                3: "UPVOTE",
                4: "COLLECT",
                5: "TIP",
                6: "FOLLOW_REV",
                7: "COMMENT_REV",
                8: "QUOTE_REV",
                9: "UPVOTE_REV",
                10: "COLLECT_REV",
                11: "TIP_REV",
                12: "CO-OWNER",
                13: "SIMILARITY",
            }

            # Map indices to profile_ids
            profile_ids = df_meta["profile_id"].astype(str).tolist()

            edges = []
            for i, (src_idx, tgt_idx) in enumerate(zip(source_indices, target_indices)):
                try:
                    src_pid = profile_ids[src_idx]
                    tgt_pid = profile_ids[tgt_idx]

                    # Resolve Weight
                    w = (
                        weights_list[i]
                        if weights_list and i < len(weights_list)
                        else 1.0
                    )

                    # Resolve Type
                    t_int = types_list[i] if types_list and i < len(types_list) else -1
                    t_str = INT_TO_EDGE_TYPE.get(t_int, "UNKNOWN")

                    # Build attribute dictionary
                    edge_data = {"weight": float(w), "edge_type": t_str}

                    edges.append((src_pid, tgt_pid, edge_data))
                except IndexError:
                    # Log but continue if indices are slightly out of sync
                    continue

            G.add_edges_from(edges)
        else:
            logger.warning("No edge_index found in the PyG data object.")

        return G

    except Exception as e:
        logger.exception(f"Unexpected error loading graph backbone: {e}")
        return nx.MultiDiGraph()
