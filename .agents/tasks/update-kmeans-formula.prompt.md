---
description: "Update the K-Means cluster count formula in modal_app.py to use an empirical square-root heuristic based on research benchmarks."
agent: "edit"
tools: ["read_file", "write_file"]
---

# Implement Empirical K-Means Formula in Modal Worker

You are an expert Data Engineer and Machine Learning Developer. Your task is to update the K-Means clustering logic in `modal_app.py` to use a dynamic formula for determining the number of clusters (`n_clusters`), replacing the current hardcoded limitation.

## Task Section

Currently, `train_gae_pipeline` limits the number of clusters strictly to 10: `n_clusters = min(10, num_nodes) if num_nodes > 0 else 1`.
Based on research benchmarks, a graph of 300 nodes optimally forms 21 clusters. We want to apply an interpolation formula based on sub-linear growth: `K = 21 * sqrt(N / 300)`.

You must replace the current static calculation with this new empirical formula while ensuring mathematical safety (integer casting, lower and upper bounds).

## Instructions Section

**Step 1: Update `n_clusters` calculation**
Locate the "5) KMeans & Heuristics" section inside the `train_gae_pipeline` function.
Replace the existing `n_clusters` assignment with the following safe calculation logic:

```python
    if num_nodes > 0:
        import math
        # Apply interpolation formula based on 300-node benchmark
        calculated_k = int(21 * math.sqrt(num_nodes / 300.0))
        # Ensure K is at least 1, and no greater than the total number of nodes
        n_clusters = max(1, min(num_nodes, calculated_k))
    else:
        n_clusters = 1
```

**Step 2: Verify the KMeans initialization**
Ensure `kmeans = KMeans(n_clusters=n_clusters, ...)` is using the newly calculated variable. Leave the other parameters like `random_state` or `n_init` untouched.

## Context/Input Section

- File to modify: `modal_worker/modal_app.py`
- Target function: `train_gae_pipeline(payload: dict)`

## Quality/Validation Section

- The logic MUST explicitly handle `num_nodes == 0` to prevent division by zero or negative square roots.
- The `min(num_nodes, calculated_k)` is critical. If a graph has 5 nodes, the formula might calculate a number higher than 5, which would cause scikit-learn's KMeans to crash. The clamp prevents this.
- Do not modify the rest of the Heuristics scoring loops below this section.
