---
description: "Fix feature vector dimensionality mismatch in modal_app.py to achieve exact 396D (384 Text + 12 Stats) matching the research training pipeline."
agent: "edit"
tools: ["read_file", "write_file", "execute_command"]
---

# Fix Dimensionality Mismatch in Modal Worker (391D to 396D)

You are an expert Data Engineer and Machine Learning Developer specializing in PyTorch Geometric (PyG), Data Preprocessing, and Modal serverless deployments. You write clean, robust, and highly optimized data pipelines.

## Task Section

The current implementation in `modal_app.py` builds a 391-dimensional node feature vector (384D Text + 7D Stats). However, the trained GNN models expect exactly **396 dimensions** (384D Text + 12D Stats).

Your task is to modify `modal_app.py` to fetch the missing on-chain statistics from BigQuery, compute missing derived metrics, and construct the correct 12-dimensional numeric vector for each node before concatenating it with the 384-dimensional text embeddings.

## Instructions Section

1. **Update BigQuery SQL (`fetch_bigquery_data`):**
   - Locate the `query_nodes` SQL string.
   - Add the missing columns from the `lens-protocol-mainnet.account.post_summary` (alias `ps`) table to the `SELECT` clause:
     - `ANY_VALUE(ps.total_tips) as total_tips`
     - `ANY_VALUE(ps.total_quotes) as total_quotes`
     - `ANY_VALUE(ps.total_reacted) as total_reacted`
     - `ANY_VALUE(ps.total_reactions) as total_reactions`

2. **Calculate `days_active`:**
   - In `fetch_bigquery_data` (after fetching the DataFrame), calculate a new column `days_active`.
   - Formula: Convert `created_on` to datetime (UTC timezone-aware), subtract it from the current UTC timestamp, and extract the total `.days`. Fill any NaN values with `0`.

3. **Update Data Imputation (`cols_to_fix`):**
   - Expand the `cols_to_fix` list to include the newly added columns (`total_tips`, `total_quotes`, `total_reacted`, `total_reactions`) as well as `trust_score`.
   - Ensure all missing numeric values in these columns are filled with `0`.

4. **Update Feature Concatenation (`build_pyg_graph`):**
   - Locate the loop where `onchain_features_raw` is constructed.
   - Modify the appended list to contain exactly these **12 features in this specific order** (matching the research pipeline):
     1. `trust_score`
     2. `total_tips`
     3. `total_posts`
     4. `total_quotes`
     5. `total_reacted`
     6. `total_reactions`
     7. `total_mirrors` (reposts)
     8. `total_collects`
     9. `total_comments`
     10. `total_followers`
     11. `total_following`
     12. `days_active`
   - _Note: Remove `has_avatar` from the numeric feature array to ensure the count is exactly 12._

## Context/Input Section

- Target file: `modal_worker/modal_app.py` (or the relative path to `modal_app.py` in the workspace).
- The text embedding is handled by `SentenceTransformer('all-MiniLM-L6-v2')` which outputs 384D.
- 384 (Text) + 12 (On-chain Stats) = 396D.

## Output Section

- Edit the `modal_app.py` file directly using your tools.
- Do not change the overall architecture or remove existing GAE/FastAPI code.
- Ensure the code handles potential `None` or `NaN` values gracefully before applying `MinMaxScaler`.

## Quality/Validation Section

- The BigQuery SQL syntax must remain valid.
- The `onchain_features_raw` list inside the loop must append exactly 12 `float()` values per node.
- The final PyG `Data` object must have `x.size(1) == 396`.
