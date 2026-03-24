---
description: "Fix semantic mismatch in LABEL_MAP and RISK_LEVELS inside inference_service.py to align with the training phase's 4-class taxonomy."
agent: "edit"
tools: ["read_file", "write_file"]
---

# Align Inference Labels with Training Taxonomy

You are an expert Backend Engineer. Your task is to fix a semantic mismatch in `app/services/inference_service.py` where the label dictionaries do not match the original Data Science training taxonomy.

## Task Section

Currently, `inference_service.py` maps class 2 to `MEDIUM_RISK` and class 3 to `HIGH_RISK`.
The actual models were trained to predict:

- Class 0: BENIGN
- Class 1: LOW_RISK
- Class 2: HIGH_RISK
- Class 3: MALICIOUS

You must update the dictionaries to correctly reflect this severity scale so the Frontend Dashboard receives the accurate alert levels.

## Instructions Section

**Step 1: Update `LABEL_MAP`**
Locate `LABEL_MAP` at the top of `app/services/inference_service.py` and change it to:

```python
LABEL_MAP = {
    0: "BENIGN",
    1: "LOW_RISK",
    2: "HIGH_RISK",
    3: "MALICIOUS"
}
```

**Step 2: Update `RISK_LEVELS`**
Locate `RISK_LEVELS` right below it and change it to align with the new labels:

```python
RISK_LEVELS = {
    0: "Clean / Genuine",
    1: "Low Risk / Possible Automation",
    2: "High Risk / Suspicious Relationships",
    3: "Malicious / Sybil Cluster Detected"
}
```

## Context/Input Section

- File to modify: `app/services/inference_service.py`

## Quality/Validation Section

- Ensure there are no syntax errors (missing commas or brackets) in the dictionaries.
- Do not modify the rest of the inference logic (`evaluate_subgraph` or `generate_reasoning`).
