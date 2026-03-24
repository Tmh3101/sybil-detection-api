---
description: "Refactor SIM_BIO edge creation in fallback_service.py to use a global graph search instead of a restricted 1-hop/2-hop neighborhood, ensuring isolated Sybil nodes are detected."
agent: "edit"
tools: ["read_file", "write_file"]
---

# Fix SIM_BIO Blindspot: Global Vector Search

You are an expert Backend Engineer and ML Ops Specialist. Your task is to fix a logic flaw in `app/services/fallback_service.py` where the NLP similarity check (`SIM_BIO`) fails to evaluate isolated nodes because it restricts its search space to 1-hop and 2-hop neighbors.

## Task Section

Currently, inside `fetch_and_embed_node`, the `SIM_BIO` logic builds a `neighbors_to_check` set by traversing `hop1` and `hop2` edges. If a newly fetched node has no physical interactions (0 edges), `hop1` is empty, and the NLP similarity check is completely skipped.

This creates a blindspot for disjoint Sybil clusters (botnets that share copy-pasted bios but do not interact with each other).
You must replace the hop-traversal logic with a global graph selection.

## Instructions Section

**Step 1: Locate the target code**
Open `app/services/fallback_service.py` and find the `# 3.5 SIMILARITY edges (NLP Bio)` section inside the `fetch_and_embed_node` function.

**Step 2: Identify the Hop Logic block**
Locate these specific lines:

```python
                    # Optimize: Check 1-hop, 2-hop neighbors
                    hop1 = set(G.successors(node_data["profile_id"])) | set(G.predecessors(node_data["profile_id"]))
                    hop2 = set()
                    for n in hop1:
                        hop2 |= set(G.successors(n)) | set(G.predecessors(n))

                    neighbors_to_check = (hop1 | hop2) - {node_data["profile_id"]}
```

**Step 3: Replace with Global Selection**
Delete the lines identified in Step 2 entirely. Replace them with a single line that collects all nodes currently in `G`, excluding the target node itself:

```python
                    # Global Search: Compare against all nodes currently in the RAM graph
                    neighbors_to_check = [n for n in G.nodes() if n != node_data["profile_id"]]
```

**Step 4: Preserve everything else**
Do NOT modify the loop that follows:

```python
                    valid_neighbors = []
                    neighbor_bios = []
                    for n_id in neighbors_to_check:
                        n_bio = G.nodes[n_id].get("bio")
                        ...
```

Do NOT modify the `SentenceTransformer` encoding or the `util.cos_sim` execution. The downstream code already filters out invalid bios perfectly.

## Context/Input Section

- File to modify: `app/services/fallback_service.py`
- Performance note: The `G.nodes()` in RAM is strictly capped (~2000-4000 nodes), so PyTorch's vector multiplication will compute the similarities in milliseconds. Global search is completely safe here.

## Quality/Validation Section

- Ensure exact indentation is maintained within the `try...except` block.
- The `node_data["profile_id"]` MUST be excluded from `neighbors_to_check` so the node does not form a `SIM_BIO` edge with itself.
