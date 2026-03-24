---
description: "Optimize modal_app.py by injecting dynamic hyperparameters from the payload and adding safety LIMITs to BigQuery SQL to prevent OOM/Timeout."
agent: "edit"
tools: ["read_file", "write_file"]
---

# Optimize Payload Parameters and SQL Limits in Modal Worker

You are an expert Backend Engineer and Database Architect. Your task is to make the GAE training pipeline in `modal_app.py` dynamic and safe for production by extracting hyperparameters from the request payload and implementing strict SQL limits.

## Task Section

Currently, `modal_app.py` hardcodes hyperparameters (`max_epochs`, `patience`, `learning_rate`) and pulls an unlimited number of nodes/edges from BigQuery, which risks OOM (Out of Memory) and Timeout errors on Modal.

You must:

1. Extract configuration parameters from the `payload` dictionary with safe clamped boundaries.
2. Pass a `max_nodes` parameter to the BigQuery fetching function.
3. Update the SQL queries to enforce this limit so the system only processes a manageable subgraph.

## Instructions Section

**Step 1: Extract and Clamp Payload Variables**
Inside `train_gae_pipeline(payload: dict)`, right after parsing `time_range`, extract the following parameters. You MUST clamp them using `min()` and `max()` to prevent malicious or absurd values from crashing the worker:

- `max_nodes`: extract from `payload.get("max_nodes", 2000)`. Clamp between `100` and `10000`.
- Extract a `hyperparameters` dict: `hp = payload.get("hyperparameters", {})`
- `max_epochs`: extract from `hp.get("max_epochs", 400)`. Clamp between `50` and `1000`.
- `patience`: extract from `hp.get("patience", 30)`. Clamp between `10` and `100`.
- `learning_rate`: extract from `hp.get("learning_rate", 0.005)`. Clamp between `0.0001` and `0.1`.

**Step 2: Update `fetch_bigquery_data` Signature**

- Modify the function signature to accept the new parameter:
  `def fetch_bigquery_data(start_date: str, end_date: str, max_nodes: int = 2000):`
- Update the function call inside `train_gae_pipeline` to pass this variable:
  `df_nodes, df_edges = fetch_bigquery_data(start_date, end_date, max_nodes=max_nodes)`

**Step 3: Enforce SQL LIMITs in BigQuery**
Inside `fetch_bigquery_data`, update the SQL queries to respect `max_nodes`:

1. **`query_nodes`**: Append `LIMIT {max_nodes}` at the very end of the query (after the `GROUP BY` clause). To ensure consistent subgraphs, add an `ORDER BY ANY_VALUE(meta.created_on) DESC` right before the `LIMIT` so it fetches the most recent active nodes first.
2. **`query_edges_follow` & `query_edges_interact`**: Both of these queries use a `WITH TargetUsers AS (...)` CTE. You MUST update this CTE to exactly mirror the limiting logic of `query_nodes`.
   _Example CTE update:_
   ```sql
   WITH TargetUsers AS (
       SELECT account
       FROM `lens-protocol-mainnet.account.metadata`
       WHERE created_on >= '{start_date}' AND created_on < '{end_date}'
       ORDER BY created_on DESC
       LIMIT {max_nodes}
   )
   ```

**Step 4: Clean Up Hardcoded Values**

- Remove any existing hardcoded declarations of `max_epochs`, `patience`, and `learning_rate` inside `train_gae_pipeline` to ensure the dynamic variables from Step 1 are the only ones used by the training loop and optimizer.

## Context/Input Section

- File to modify: `modal_worker/modal_app.py`
- BigQuery dialect: Standard SQL.
- Python clamping trick: `max(min_val, min(extracted_val, max_val))`

## Quality/Validation Section

- The BigQuery queries MUST remain syntactically valid. Pay close attention to the order of `GROUP BY`, `ORDER BY`, and `LIMIT`.
- The edge queries must only fetch edges where BOTH `source` and `target` belong to the limited `TargetUsers` pool. The existing `JOIN TargetUsers t1 ... JOIN TargetUsers t2` logic already handles this, but the CTE itself must have the `LIMIT`.
- The optimizer initialization (`torch.optim.Adam`) must use the dynamic `learning_rate`.
