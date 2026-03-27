---

## description: "Backend: Expand GAT attention extraction to all edges (Depth 1 & 2) across both layers"
agent: "edit"
tools: ["editFiles", "codebase"]

# Phase 1: Global GAT Attention Extraction (Depth 1 & 2)

You are an expert Machine Learning and FastAPI Backend Engineer. Our current system only extracts GAT attention for edges directly connected to the `target_id`. We need to expand this to cover EVERY edge in the local ego-graph (Depth 1 and Depth 2) using weights from both GAT layers.

## Core Objective

1. **Multi-layer weights:** Extract attention from both `conv1` (explaining Depth 2 -> Depth 1) and `conv2` (explaining Depth 1 -> Target).
2. **Global assignment:** Assign `gat_attention` to every edge returned in the Inspector response, not just target-centric ones.

## Step-by-Step Instructions

### Step 1: Update Model Forward Pass (`app/core/model_loader.py`)

1. Open `app/core/model_loader.py`.
2. Locate the `GATClassifier` class.
3. Modify the `forward` method to return attention weights from BOTH layers:
  - Call `self.conv1(..., return_attention_weights=True)` and capture `(idx1, w1)`.
  - Call `self.conv2(..., return_attention_weights=True)` and capture `(idx2, w2)`.
  - Return a tuple: `return x, (idx1, w1), (idx2, w2)`.

### Step 2: Update Inference Logic (`app/services/inference_service.py`)

1. Open `app/services/inference_service.py`.
2. Locate the `analyze_profile` function.
3. Update the GAT model call to catch the three return values:
  `embeddings, attn_l1, attn_l2 = models["gat_model"](x, edge_index, edge_attr)`
4. **Logic for Weight Merging:** Create a unified `attention_map` dictionary where the key is `(source_id, target_id)`.
  - Iterate through `attn_l1`: Map tensor indices to real wallet IDs and store the float weight value.
  - Iterate through `attn_l2`: Map and store. If a connection exists in both maps, take the **Maximum (MAX)** value.
  - *Tip:* Use `idx_to_node = {i: n_id for n_id, i in node_to_idx.items()}` for fast mapping.
5. **Remove Filtering Logic:** Locate the loop that iterates through `subgraph.edges(data=True)`.
  - **DELETE** the condition `if u == target_id or v == target_id:`.
  - For **every** edge `(u, v)`, look up its weight in your `attention_map`.
  - Assign the result: `subgraph[u][v][0]['gat_attention'] = attention_map.get((u, v), 0.0)`.

### Step 3: Verify Schema & Service Response

1. Ensure the `InspectorService` correctly serializes the NetworkX graph with the new edge attributes.
2. If `edge_attentions` is returned as a separate list in the final JSON, ensure it contains all edges from the subgraph.

## Implementation Details & Constraints

- **Performance:** Use `cpu().numpy()` on tensors before looping to ensure efficiency.
- **Aggregation:** Taking the `MAX` attention between layers is preferred as it highlights the strongest signal used by the GNN for that specific connection.
- **Type Safety:** Ensure all tensor values are cast to Python `float` to avoid JSON serialization errors.
- **Radius:** The subgraph is already radius=2, ensure your logic iterates over all edges retrieved.

## Quality Validation

- **Success Criteria:** The API response for Module 2 should now have non-zero `gat_attention` values for edges that do NOT connect to the target node.
- **Robustness:** Ensure self-loops (node connecting to itself) are handled or safely ignored.

