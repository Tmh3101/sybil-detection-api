---
description: "Refactor Heuristics Labeling in modal_app.py from Node-level to Cluster-level (Top-down scoring) matching the fullflow.py research logic."
agent: "edit"
tools: ["read_file", "write_file"]
---

# Refactor Sybil Heuristics Scoring to Cluster-Level

You are an expert Data Scientist and Python Developer. Your task is to refactor the rule-based labeling logic (Heuristics) in `modal_app.py` to match the exact cluster-level statistical approach used in the original research pipeline.

## Task Section

Currently, `modal_app.py` calculates risk scores individually for each node by looking at its direct edges (`CO-OWNER` +0.5, `SIMILARITY` +0.3, etc.). This causes inconsistent labels compared to the research.

You must rewrite the "5) KMeans & Heuristics" section inside the `train_gae_pipeline` function. The new logic must evaluate entire **Clusters** by calculating the percentage of internal edge types, applying the additive 100-point scoring system, and then assigning the final label to ALL nodes within that cluster.

## Instructions Section

**Step 1: Map Nodes to Clusters**

- After `cluster_ids = kmeans.fit_predict(node_embeddings)`, create a dictionary mapping `profile_id` to its `cluster_id`.

**Step 2: Filter Internal Edges**

- Iterate through `edges_list`. Only keep "internal edges" where both the `source` and `target` belong to the SAME `cluster_id`.
- Group these internal edges by `cluster_id`.

**Step 3: Calculate Cluster Statistics**
Iterate through each unique `cluster_id` (0 to `n_clusters - 1`) and compute:

1. `size`: Number of nodes in this cluster.
2. `total_internal_edges`: Count of internal edges (if 0, set to 1 to avoid division by zero).
3. `pct_co_owner`: (Count of `CO-OWNER` edges) / `total_internal_edges`.
4. `pct_similarity`: (Count of `SIMILARITY` edges) / `total_internal_edges`.
5. `pct_social`: (Count of `FOLLOW`, `COMMENT`, `QUOTE` edges) / `total_internal_edges`.
6. `avg_trust`: Mean `trust_score` of all nodes in the cluster.
7. `std_creation_hours`: Calculate the standard deviation of the `created_on` datetime for nodes in this cluster (in hours). If `size == 1`, set to 0. _(Note: you will need to convert `created_on` from `df_nodes` to pandas datetime)._

**Step 4: Apply Additive Risk Scoring (0 - 100)**
For each cluster, initialize `score = 0` and a `reasons = []` list. Apply these rules:

- **Co-owner:** If `pct_co_owner > 0.1` -> `score += 50`, append reason.
- **Similarity:** If `size > 2` AND `pct_similarity >= 0.6` -> `score += 30`, append reason.
- **Batch Creation:** If `size > 1` AND `std_creation_hours < 0.5` -> `score += 15`, append reason.
- **Low Social:** If `pct_social <= 0.2` -> `score += 10`, append reason.
- **Low Trust:** If `avg_trust <= 5` -> `score += 20` ELIF `avg_trust <= 8` -> `score += 10`, append reason.

Cap the final `score` at 100. Normalize to `0.0 - 1.0` (i.e., `risk_score = score / 100.0`) for the output.

**Step 5: Fuzzy Labeling**
Determine the cluster's label based on the 100-point score:

- `< 20`: `"0_BENIGN"`
- `<= 50`: `"1_LOW_RISK"`
- `< 80`: `"2_HIGH_RISK"`
- `>= 80`: `"3_MALICIOUS"`

**Step 6: Assign to Nodes**

- Store the calculated `label`, `risk_score`, and `reason` for each `cluster_id`.
- Update the final `nodes` formatting loop so every node inherits its cluster's `label` and `risk_score`. Also, add a `"reason"` field inside the `attributes` dictionary of the node output.

## Context/Input Section

- File to modify: `modal_worker/modal_app.py`
- Note: `pct_fuzzy_handle` from the original research is omitted here because the edge type doesn't exist in the Modal app. We will proceed with the remaining 5 criteria.

## Quality/Validation Section

- The logic MUST evaluate edges at the cluster level, not the node level.
- Ensure Pandas datetime operations for `std_creation_hours` handle NaNs and timezone issues safely.
- Do not break the return schema `{"nodes": nodes, "links": links}`.
