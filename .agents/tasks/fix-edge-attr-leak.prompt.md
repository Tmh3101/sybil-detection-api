---
description: "Fix edge attribute data leak in inspector_service.py by properly loading edge weights from PyG Data to NetworkX."
agent: "edit"
tools: ["read_file", "write_file"]
---

# Fix Edge Attribute Data Leak in Graph Backbone

You are an expert Backend and Machine Learning Engineer specializing in PyTorch Geometric (PyG) and NetworkX. Your task is to fix a critical data leak in `app/services/inspector_service.py`.

## Task Section

Currently, the `load_reference_graph` function reads `edge_index` from the PyG `data` object and adds edges to the NetworkX graph `G` as simple tuples: `(src_pid, tgt_pid)`.

It completely ignores `data.edge_attr`, which contains the pre-calculated edge weights. Because of this, `inference_service.py` receives `None` when querying `data.get("weight")` and is forced to fallback to static default weights, significantly degrading the GAT model's accuracy.

Your task is to extract `edge_attr` and append it as a dictionary to each edge before adding them to NetworkX.

## Instructions Section

**Step 1: Extract Edge Weights**
Inside `load_reference_graph`, right before the `edges = []` initialization, check if the PyG `data` object has `edge_attr`.
If it does, safely flatten it into a Python list. PyG's `edge_attr` is usually shape `[num_edges, 1]` or `[num_edges]`.
Example:

```python
weights_list = data.edge_attr.view(-1).tolist() if hasattr(data, "edge_attr") and data.edge_attr is not None else None
```

**Step 2: Update the Loop with Indexing**
Modify the edge loop to include an index `i` using `enumerate` so we can map each edge to its corresponding weight:

```python
for i, (src_idx, tgt_idx) in enumerate(zip(source_indices, target_indices)):
```

**Step 3: Build Edge Attribute Dictionary**
Inside the `try` block of the loop, extract the weight. If `weights_list` exists and the index is valid, use it; otherwise, default to `1.0`.

```python
w = weights_list[i] if weights_list and i < len(weights_list) else 1.0
edge_data = {"weight": float(w)}
```

**Step 4: Append Edge with Attributes**
Modify the `edges.append` statement to include the `edge_data` dictionary as the third element of the tuple. NetworkX's `add_edges_from` automatically parses the third element as edge attributes.

```python
edges.append((src_pid, tgt_pid, edge_data))
```

## Context/Input Section

- File to modify: `app/services/inspector_service.py`
- Target function: `load_reference_graph`
- Note: Keep the existing `IndexError` exception handling intact.

## Quality/Validation Section

- The script must not crash if `data` lacks `edge_attr`.
- `weights_list` must be flattened properly using `.view(-1).tolist()` to avoid extracting nested lists.
- The output tuples in the `edges` list must strictly follow the `(source, target, attr_dict)` format.
