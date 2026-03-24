---
description: "Standardize the naming of the 'repost/mirror' feature to 'total_reposts' across all services and SQL queries to ensure perfect alignment with the trained scaler.bin."
agent: "edit"
tools: ["read_file", "write_file"]
---

# Standardize Feature Schema: 'total_reposts'

You are an expert Data Engineer. Your task is to fix a silent "Schema Mismatch" bug across the application where the concept of "Mirroring" is inconsistently named, causing the Machine Learning feature vector to break.

## Task Section

The ML model's `scaler.bin` was trained on a specific 12-dimensional feature vector, where the 7th feature is exactly named `total_reposts`.
Currently, some SQL queries and dictionaries in the codebase use the alias `total_mirrors`, causing `inference_service.py` to fetch `0.0` for this crucial feature.

You must scan the specific files and enforce the naming `total_reposts` universally.

## Instructions Section

**Step 1: Fix `modal_app.py` (Module 1)**

- Locate the BigQuery SQL string inside `fetch_bigquery_data`.
- If there is a selection for `total_mirrors`, change its SQL alias to `total_reposts` (e.g., `ANY_VALUE(ps.total_mirrors) as total_reposts` OR `ANY_VALUE(ps.total_reposts) as total_reposts` depending on the actual DB column).
- Update the feature array concatenation loop: replace `float(node_row.get("total_mirrors", 0))` with `float(node_row.get("total_reposts", 0))`.

**Step 2: Fix `app/services/fallback_service.py` (Module 2)**

- Locate the BigQuery SQL inside `fetch_and_embed_node`.
- Ensure the selected column is aliased strictly as `total_reposts`.
- In the mapping dictionary `node_data = { ... }`, ensure the key is saved as `"total_reposts": row.get("total_reposts", 0)`.

**Step 3: Fix `app/services/inspector_service.py` (Module 2)**

- Inside the `load_reference_graph` loop where `G.add_node()` is called, verify that the attribute is being assigned as `total_reposts=row.get("total_reposts", 0)`. Make sure the word "mirrors" is not used here.

**Step 4: Verify `app/services/inference_service.py`**

- Check the `evaluate_subgraph` function where the `stats = [...]` array is built.
- Ensure the retrieval is exactly `attrs.get("total_reposts", 0.0)`.

## Context/Input Section

- In Lens Protocol, "Mirrors" and "Reposts" are the same concept. We are standardizing strictly on the database schema terminology: `total_reposts`.

## Quality/Validation Section

- The spelling must be exactly `total_reposts` across Python dict keys and SQL `AS` aliases.
- Do not accidentally modify `total_posts` (which means original posts, not reposts).
