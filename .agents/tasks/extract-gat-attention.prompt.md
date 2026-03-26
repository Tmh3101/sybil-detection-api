---
description: "Extract GAT attention weights and expose them via Inspector API (Module 2)"
agent: "edit"
tools: ["editFiles", "codebase"]
---

# Phase 1: Extract GAT Attention Weights for XAI (Explainable AI)

You are an expert Machine Learning Engineer and FastAPI Developer. Your task is to extract the edge attention weights from our trained Graph Attention Network (GAT) and pass them down to the API response for Module 2 (Inspector) so the frontend can visualize which edges the AI focused on.

## Step-by-Step Instructions

### Step 1: Update Model Definition (`app/core/model_loader.py`)

1. Open `app/core/model_loader.py`.
2. Locate the `GATClassifier` class and its `forward` method.
3. Modify the second GAT layer (`self.conv2`) call to request attention weights:
   Change `x = self.conv2(x, edge_index, edge_attr=edge_attr)`
   To: `x, (attn_edge_index, attn_weights) = self.conv2(x, edge_index, edge_attr=edge_attr, return_attention_weights=True)`
4. Modify the return statement of the `forward` method to return both the embeddings and the attention tuple:
   Change `return x`
   To: `return x, (attn_edge_index, attn_weights)`

### Step 2: Update Inference Service (`app/services/inference_service.py`)

1. Open `app/services/inference_service.py`.
2. Locate the `3. Inference` section inside the `analyze_profile` function (specifically the `try...except` block where `models["gat_model"]` is called).
3. Update the GAT model call to catch the new tuple:
   `embeddings, (attn_edge_index, attn_weights) = models["gat_model"](x, edge_index, edge_attr)`
4. **Attention Mapping Logic:** Right after getting the embeddings, create a mapping from tensor indices back to real wallet IDs.

   ```python
   idx_to_node = {i: n_id for n_id, i in node_to_idx.items()}
   attn_edge_index_np = attn_edge_index.cpu().numpy()
   attn_weights_np = attn_weights.cpu().numpy()

   attention_map = {}
   for i in range(attn_edge_index_np.shape[1]):
       u_idx = attn_edge_index_np[0, i]
       v_idx = attn_edge_index_np[1, i]
       weight_val = float(attn_weights_np[i][0]) if len(attn_weights_np[i]) > 0 else 0.0
       attention_map[(idx_to_node[u_idx], idx_to_node[v_idx])] = weight_val
   ```

5. **Edge Injection:** Scroll down to the `4. Reasoning & Edge Attention Assignment` section where `subgraph.edges(data=True)` is iterated.
   Inject the `gat_attention` score into each edge's data dict:
   ```python
   for u, v, data in subgraph.edges(data=True):
       gat_attention = attention_map.get((u, v), 0.0)
       # Inject into the NetworkX graph so it gets serialized automatically
       subgraph[u][v][0]['gat_attention'] = gat_attention
       # ... keep existing logic
   ```

### Step 3: Update API Schema (`app/schemas/sybil.py` or where Edge is defined)

1. Open the file defining the API response schemas (likely `app/schemas/sybil.py` or `app/schemas/inspector.py`).
2. Locate the `SybilEdge` (or equivalent link/edge) Pydantic model.
3. Add a new optional field: `gat_attention: Optional[float] = Field(default=0.0, description="GAT attention weight for this edge")`.

## Quality Constraints

- Do NOT alter the Random Forest (`rf_model`) or `StandardScaler` logic.
- Do NOT break the existing `predict_proba` structure.
- Ensure all tensor values (`attn_weights`) are converted to pure Python `float` before being put into the dictionary/graph to prevent JSON serialization errors.
