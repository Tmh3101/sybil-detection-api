---
description: "Fix edge attribute and semantic type data leak in inspector_service.py by applying the official 12-class edge taxonomy and loading data into the NetworkX Backbone."
agent: "edit"
tools: ["read_file", "write_file"]
---

# Fix Edge Attributes & Semantic Types in Graph Backbone

You are an expert Backend and PyTorch Geometric (PyG) Engineer. Your task is to fix a critical data loss issue in `app/services/inspector_service.py` where the NetworkX graph loads edges blindly, dropping both their calculated weights (`edge_attr`) and semantic types (`edge_type`).

## Task Section

Currently, `load_reference_graph` only reads `edge_index` and adds simple `(src, tgt)` tuples to NetworkX.
Because the original training script encoded string edge types into integers but failed to export the mapping dictionary, the Reasoning Engine downstream is blind to whether an edge is a benign `FOLLOW` or a malicious `CO-OWNER`.

You must extract `edge_attr` and `edge_type`, flatten them, map the integers back to strings using the official 12-class taxonomy, and inject them into NetworkX as edge attributes.

## Instructions Section

**Step 1: Extract Edge Attributes and Types**
Inside `load_reference_graph`, right before `edges = []`, safely extract and flatten both properties from the PyG `data` object:

```python
            # Safely extract and flatten weights and types
            weights_list = data.edge_attr.view(-1).tolist() if hasattr(data, "edge_attr") and data.edge_attr is not None else None
            types_list = data.edge_type.view(-1).tolist() if hasattr(data, "edge_type") and data.edge_type is not None else None
```

**Step 2: Inject the Official Mapping**
Above the edge processing loop, define this specific dictionary based on the system's official edge taxonomy:

```python
            # Official mapping from the system's WEIGHTS configuration
            EDGE_TYPE_MAP = {
                0: "FOLLOW",
                1: "UPVOTE",
                2: "REACTION",
                3: "COMMENT",
                4: "QUOTE",
                5: "MIRROR",
                6: "COLLECT",
                7: "CO-OWNER",
                8: "SAME_AVATAR",
                9: "FUZZY_HANDLE",
                10: "SIM_BIO",
                11: "CLOSE_CREATION_TIME"
            }
```

**Step 3: Update the Loop Construction**
Modify the edge loop to use `enumerate` so we can index into the extracted lists:

```python
            for i, (src_idx, tgt_idx) in enumerate(zip(source_indices, target_indices)):
                try:
                    src_pid = node_idx_to_pid[src_idx]
                    tgt_pid = node_idx_to_pid[tgt_idx]

                    # Resolve Weight
                    w = weights_list[i] if weights_list and i < len(weights_list) else 1.0

                    # Resolve Type
                    t_int = types_list[i] if types_list and i < len(types_list) else -1
                    t_str = EDGE_TYPE_MAP.get(t_int, "UNKNOWN")

                    # Build attribute dictionary
                    edge_data = {
                        "weight": float(w),
                        "type": t_str
                    }

                    edges.append((src_pid, tgt_pid, edge_data))
                except KeyError:
                    continue
```

## Context/Input Section

- Target file: `app/services/inspector_service.py`
- NetworkX `add_edges_from` automatically recognizes the third element in a `(src, tgt, dict)` tuple as edge attributes.

## Quality/Validation Section

- The system MUST NOT crash if `data.edge_attr` or `data.edge_type` is missing (it must fallback to `1.0` and `"UNKNOWN"`).
- Flattening via `.view(-1).tolist()` is mandatory to prevent injecting nested list objects like `[5.0]` into the weight attribute.
