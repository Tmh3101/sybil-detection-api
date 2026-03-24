---
description: "Fix node attribute data leak in inspector_service.py by loading all required on-chain numeric stats into the NetworkX Backbone."
agent: "edit"
tools: ["read_file", "write_file"]
---

# Fix Node Attribute Data Leak in Graph Backbone

You are an expert Backend and Machine Learning Engineer. Your task is to fix a critical data leak in `app/services/inspector_service.py` where crucial numeric features are not being loaded into the NetworkX graph.

## Task Section

Currently, the `G.add_node()` call in `load_reference_graph` only loads a few metadata fields (`handle`, `bio`, `trust_score`, etc.) from the CSV. It completely drops `total_tips`, `total_posts`, `total_followers`, and other on-chain statistics.

Because of this, `inference_service.py` receives `0.0` for almost all numeric features, blinding the ML model. You must update `G.add_node()` to include all the missing fields required by the inference pipeline.

## Instructions Section

**Step 1: Identify Missing Fields**
Based on `inference_service.py`, the following 10 fields are missing and MUST be added to the node attributes:
`total_tips`, `total_posts`, `total_quotes`, `total_reacted`, `total_reactions`, `total_reposts`, `total_collects`, `total_comments`, `total_followers`, `total_following`.

**Step 2: Update `G.add_node` in `inspector_service.py`**
Locate the loop `for _, row in df_meta.iterrows():` inside `load_reference_graph`.
Expand the `G.add_node()` arguments to safely extract and include all the missing fields using `row.get()`.

Example format:

```python
        G.add_node(
            str(row["profile_id"]),
            handle=row.get("handle"),
            picture_url=row.get("picture_url"),
            owned_by=row.get("owned_by"),
            bio=row.get("bio", ""),
            created_on=row.get("created_on"),
            trust_score=row.get("trust_score"),
            total_tips=row.get("total_tips", 0),
            total_posts=row.get("total_posts", 0),
            total_quotes=row.get("total_quotes", 0),
            total_reacted=row.get("total_reacted", 0),
            total_reactions=row.get("total_reactions", 0),
            total_reposts=row.get("total_reposts", 0),
            total_collects=row.get("total_collects", 0),
            total_comments=row.get("total_comments", 0),
            total_followers=row.get("total_followers", 0),
            total_following=row.get("total_following", 0)
        )
```

## Context/Input Section

- File to modify: `app/services/inspector_service.py`
- Note: Use a default of `0` in `row.get("key", 0)` to prevent `None` values from crashing the downstream scaler if the CSV is missing a column.

## Quality/Validation Section

- Do not remove any existing attributes (`handle`, `picture_url`, etc.).
- Ensure the spelling of the keys strictly matches the `attrs.get(...)` calls in `inference_service.py`.
