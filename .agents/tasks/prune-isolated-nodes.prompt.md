---
description: "Refactor build_pyg_graph to prune isolated nodes before feature extraction"
agent: "edit"
tools: ["editFiles"]
---

# Prune Isolated Nodes in PyG Graph Pipeline

You are an expert Data Engineer and Machine Learning Engineer specializing in PyTorch Geometric (PyG), Pandas data manipulation, and graph data processing pipelines.

## Task

Your primary task is to update the `build_pyg_graph` function in the provided codebase to identify and remove isolated nodes (nodes without any edges) _before_ executing the computationally expensive SentenceTransformer embeddings and feature scaling.

## Instructions

Please follow this step-by-step process strictly:

1. **Reorder Edge Logic**: Move the edge creation logic (extracting from `df_edges`, building CO-OWNER edges, and building SIMILARITY edges) to the very beginning of the function.
2. **Identify Connected Nodes**: Create a `Set` of all unique node IDs that appear as either a `source` or `target` in the compiled edge list.
3. **Prune DataFrame**: Filter the `df_nodes` DataFrame to keep _only_ the rows where `profile_id` exists in the connected nodes set.
4. **Re-index**: Rebuild the `node_ids` list and `id_to_idx` mapping based on the newly pruned `df_nodes`.
5. **Clean Edges**: Filter the edge list one more time to ensure no edges reference nodes that might have been dropped (safeguard step).
6. **Optimized Feature Extraction**: Run the `SentenceTransformer` text encoding and `MinMaxScaler` on-chain feature scaling _only_ on the pruned `df_nodes`.
7. **Build PyG Data**: Construct the final `edge_index`, `edge_attr`, and concatenated `x` tensor, then return the `Data` object, `node_ids`, and `edges_list`.

## Context / Input

- Target file: `${file}` (The user will have `modal_app.py` open).
- **Goal**: Save compute resources (RAM/GPU) by not embedding isolated nodes, and clean up the downstream UI graph visualization.

## Output

- Output format: Code.
- Modify the existing `build_pyg_graph` function in the current file directly.
- Ensure the code is clean, maintains existing variable names where possible, and includes brief comments explaining the pruning step.
- Do not remove the `all-MiniLM-L6-v2` logic or the 12 on-chain features logic; just apply them _after_ the pruning.

## Quality & Validation

- **Success Criteria 1**: The length of `node_ids` returned must strictly be <= the original length of `df_nodes`.
- **Success Criteria 2**: SentenceTransformer (`model.encode()`) must only process the text data of connected nodes.
- **Success Criteria 3**: The PyG `Data` object must have matching dimensions for `x` (nodes \* features) and `edge_index` without out-of-bounds indices.
