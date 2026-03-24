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
        logger.warning(f"Data files not found: {pt_path} or {meta_path}. Returning empty graph.")
        return nx.MultiDiGraph()

    try:
        # Load data in a separate thread to avoid blocking the event loop
        def sync_load():
            # Using weights_only=False because PyG Data objects are often complex pickles
            # and map_location='cpu' as instructed.
            data = torch.load(pt_path, map_location="cpu", weights_only=False)
            df_meta = pd.read_csv(meta_path)
            return data, df_meta

        data, df_meta = await asyncio.to_thread(sync_load)

        # Basic validation
        num_nodes_pt = data.num_nodes if hasattr(data, 'num_nodes') else data.x.size(0)
        if num_nodes_pt != len(df_meta):
            logger.error(f"Mismatch: num_nodes ({num_nodes_pt}) != len(df_meta) ({len(df_meta)})")
            return nx.MultiDiGraph()

        G = nx.MultiDiGraph()

        # Add Nodes
        # Expected columns in metadata: profile_id, handle, picture_url, owned_by
        # Using profile_id as the node key
        logger.info(f"Adding {len(df_meta)} nodes to Backbone...")
        for _, row in df_meta.iterrows():
            G.add_node(
                str(row["profile_id"]),
                handle=row.get("handle"),
                display_name=row.get("display_name"),
                picture_url=row.get("picture_url"),
                owned_by=row.get("owned_by"),
                bio=row.get("bio", ""),
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
                total_following=row.get("total_following", 0)
            )

        # Add Edges
        # edge_index is [2, num_edges]
        if hasattr(data, "edge_index"):
            logger.info(f"Adding {data.edge_index.size(1)} edges to Backbone...")
            source_indices = data.edge_index[0].tolist()
            target_indices = data.edge_index[1].tolist()
            
            # Extract weights if available
            weights_list = data.edge_attr.view(-1).tolist() if hasattr(data, "edge_attr") and data.edge_attr is not None else None
            
            # Map indices to profile_ids
            profile_ids = df_meta["profile_id"].astype(str).tolist()
            
            edges = []
            for i, (src_idx, tgt_idx) in enumerate(zip(source_indices, target_indices)):
                try:
                    src_pid = profile_ids[src_idx]
                    tgt_pid = profile_ids[tgt_idx]
                    
                    # Build edge attribute dictionary
                    w = weights_list[i] if weights_list and i < len(weights_list) else 1.0
                    edge_data = {"weight": float(w)}
                    
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
