---
description: "Fix dictionary overwrite bug in GAT attention weight mapping for multi-graph edges."
agent: "edit"
tools: ["file_search", "read_file", "edit_file"]
---

# Fix GAT Attention Mapping Bug

You are an Expert Python Backend Engineer specializing in FastAPI and PyTorch Geometric (PyG).
Currently, the API response for the Sybil Inspector is returning identical `gat_attention` scores for different edges that share the same `(source, target)` pair (e.g., a CO-OWNER edge and a FOLLOW edge between Node A and Node B get the exact same attention score).

This is not a model issue, but a **Dictionary Overwrite Bug** in the service layer mapping logic.

## 🎯 Task Section

Locate the code responsible for mapping attention weights from the PyG model output back to the JSON response dictionaries. Change the mapping logic from a `(source, target)` dictionary approach to a direct `1:1 index-based` approach.

## 📋 Instructions Section

### Step 1: Locate the Bug

**Files to check/modify:** `app/services/inspector_service.py` (and `app/services/inference_service.py` if it shares the same logic).

1. Look for the section where the model is invoked: `x, (idx1, w1), _ = model(...)` or similar.
2. Identify the flawed dictionary mapping logic that looks like this:
   ```python
   att_dict = {}
   for i in range(...):
       att_dict[(src, tgt)] = w1[i].mean().item()
   ```

### Step 2: Implement Index-Based Mapping

Replace the dictionary logic with direct index mapping. PyTorch Geometric guarantees that the first `E` elements in the attention output `w1` correspond exactly 1:1 with the input `edge_index` (and consequently, your `response_edges` list).

_Crucial Note:_ `GATv2Conv` automatically adds self-loops, so the length of `w1` is `E + N` (Edges + Nodes). You MUST slice the tensor to only take the first `E` edges.

Implement this exact logic replacement:

```python
# 1. Get the exact number of original edges
num_original_edges = len(response_edges)

# 2. Slice the first E edges, average across attention heads, and convert to list
attention_scores = w1[:num_original_edges].mean(dim=1).tolist()

# 3. Map directly by index
for i, edge in enumerate(response_edges):
    edge['gat_attention'] = attention_scores[i]
```

## Context/Input Section

- The model in use is `GATv2Conv`, which outputs attention weights `w1` with shape `[E + N, heads]`.
- We are dealing with a Multi-graph. Two nodes can have multiple distinct edges between them (e.g., `weight: 10.0` vs `weight: 0.5`).
- Dictionary mapping with `(source, target)` as keys silently overwrites previous edges, causing the frontend to display duplicate attention scores.

## ✅ Quality/Validation Section

1. Verify that `app/services/inspector_service.py` no longer uses `att_dict[(src, tgt)]`.
2. Ensure the slicing `[:num_original_edges]` is present so the zip/enumerate doesn't go out of bounds or assign self-loop attention to real edges.
3. Ensure no syntax errors or variable misalignments are introduced during the refactor.
