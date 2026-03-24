---
description: "Integrate pre-computed bio embeddings into the Graph Backbone and refactor SIM_BIO to use fast tensor matrix multiplication."
agent: "edit"
tools: ["read_file", "write_file"]
---

# Integrate Pre-computed Bio Embeddings for Fast Global Search

You are an expert Backend Engineer and Machine Learning Systems Architect specializing in FastAPI, PyTorch, and NetworkX.

## Task Section

The user has successfully generated a `bio_embeddings.pt` file containing a dictionary that maps `profile_id` (string) to 384-dimensional PyTorch tensors.
Your task is to integrate this file into the backend to eliminate the NLP encoding bottleneck. You will:

1. Update `inspector_service.py` to load this file on startup and attach the vectors to the RAM graph nodes.
2. Refactor the `SIM_BIO` logic in `fallback_service.py` to utilize these cached tensors for instantaneous $O(N)$ matrix multiplication, replacing the slow loop-based re-encoding.

## Instructions Section

**Step 1: Update `inspector_service.py`**

- Locate the `load_reference_graph` function.
- Inside the function, dynamically resolve the embedding path right before the `sync_load` definition:
  `emb_path = os.path.join(os.path.dirname(pt_path), "bio_embeddings.pt")`
- Update `sync_load()` to read this file using `torch.load(emb_path, map_location="cpu", weights_only=False)` if `os.path.exists(emb_path)` is True. Store it in a dictionary named `bio_embs` and return it alongside `data` and `df_meta`.
- Inside the `for _, row in df_meta.iterrows():` loop, update the `G.add_node()` call to include a new attribute: `bio_embedding=bio_embs.get(str(row["profile_id"]), None)`.

**Step 2: Update `fallback_service.py`**

- Locate the `# 3.5 SIMILARITY edges (NLP Bio)` section inside the `fetch_and_embed_node` function.
- Replace the entire existing logic under `if new_bio and isinstance(new_bio, str) and len(new_bio.strip()) > 5:` with the following optimized matrix operations:
  1. Encode ONLY the new user's bio ONCE: `new_bio_tensor = model.encode([new_bio], convert_to_tensor=True)`
  2. Initialize `valid_neighbors = []` and `existing_embs = []`.
  3. Iterate through `G.nodes(data=True)`. If `n_id == node_data["profile_id"]`, `continue`. Otherwise, extract `cached_emb = attrs.get("bio_embedding")`. If it exists, append to the lists.
  4. If `valid_neighbors` is not empty, use `torch.stack(existing_embs)` to create a 2D matrix.
  5. Compute scores using `util.cos_sim(new_bio_tensor, existing_matrix)[0]`.
  6. Loop through `scores` with `enumerate`; if `score.item() >= 0.85`, extract `target_pid = valid_neighbors[idx]` and add bidirectional `SIM_BIO` edges between `node_data["profile_id"]` and `target_pid`.

## Context/Input Section

- Target files: `app/services/inspector_service.py` and `app/services/fallback_service.py`.
- The `bio_embeddings.pt` file is located in the same directory as `graph.pt`.
- The dictionary keys in `bio_embeddings.pt` are strings, so ensure `str(row["profile_id"])` is used when looking up embeddings.

## Output Section

- Directly apply code edits to both `inspector_service.py` and `fallback_service.py`.
- Preserve all existing imports.
- Ensure `import os` is present in `inspector_service.py`.
- Ensure `import torch` and `from sentence_transformers import util` are imported within the SIM_BIO block (or at the top of the file) in `fallback_service.py`.

## Quality/Validation Section

- The application MUST NOT crash if `bio_embeddings.pt` is missing (it must safely default to an empty dictionary).
- The `fallback_service.py` MUST NOT call `model.encode` inside any loop.
- Ensure `node_data["profile_id"]` is explicitly skipped so the node does not calculate similarity against itself.
- All existing attributes in `G.add_node` (like `total_posts`, `trust_score`) must remain completely intact.
