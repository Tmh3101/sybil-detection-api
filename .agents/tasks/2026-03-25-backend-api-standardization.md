# Implementation Plan: Backend Inference API Refactoring (ML Standards)

## 🎯 Overview

This plan focuses on refactoring the Backend (FastAPI) inference service to align its JSON output with standard Machine Learning naming conventions (`predict_label` and `predict_proba`). We will remove the ambiguous `risk_score` / `sybil_probability` and instead return the exact prediction label and the full class probability distribution.

**Expected JSON Output:**

```json
"analysis": {
  "predict_label": "HIGH_RISK",
  "predict_proba": {
    "BENIGN": 0.20,
    "LOW_RISK": 0.05,
    "HIGH_RISK": 0.65,
    "MALICIOUS": 0.10
  },
  "reasoning": [ ... ]
}
```

## 📁 File Structure Mapping

- `app/services/inference_service.py`: Update the return dictionary.
- `app/schemas/inspector.py` (or relevant schema): Update Pydantic models.

---

## 🛠️ Execution Tasks & Checklist

### Task 1: Refactor Inference Logic (`inference_service.py`)

**Objective:** Replace `risk_score` with `predict_proba` and `predict_label`.

- [ ] Open `app/services/inference_service.py`.
- [ ] Locate the `evaluate_subgraph` function.
- [ ] Extract the probability array safely: `probs = rf_model.predict_proba(scaled_embedding)[0]`.
- [ ] Determine the predicted class index: `rf_pred_class = int(rf_model.predict(scaled_embedding)[0])`.
- [ ] Create the `predict_proba` dictionary mapping class names to their probabilities:
  ```python
  predict_proba = {
      "BENIGN": float(probs[0]),
      "LOW_RISK": float(probs[1]) if len(probs) > 1 else 0.0,
      "HIGH_RISK": float(probs[2]) if len(probs) > 2 else 0.0,
      "MALICIOUS": float(probs[3]) if len(probs) > 3 else 0.0
  }
  ```
- [ ] Resolve the `predict_label` string: `predict_label = LABEL_MAP.get(rf_pred_class, "UNKNOWN")`.
- [ ] Update the final return dictionary of the function. **REMOVE** `risk_score`, `label`, and `class_probabilities`. **ADD** `predict_label` and `predict_proba`.
  ```python
  return {
      "predict_label": predict_label,
      "predict_proba": predict_proba,
      "reasoning": reasoning,
      "risk_level": RISK_LEVELS.get(rf_pred_class, "Unknown")
  }
  ```

### Task 2: Update Pydantic Schemas

**Objective:** Update FastAPI schemas to validate the new structure and avoid 500 Internal Server Errors.

- [ ] Open `app/schemas/inspector.py` (or `app/schemas/sybil.py` if the analysis schema is located there).
- [ ] Locate the schema class for the analysis object (e.g., `Analysis`, `AnalysisResponse`, or similar).
- [ ] Make the following field changes:
  - **Remove:** `sybil_probability` (or `risk_score`).
  - **Remove:** `risk_label`.
  - **Add:** `predict_label: str`
  - **Add:** `predict_proba: Dict[str, float]`
- [ ] Double-check that all endpoints constructing this response type are importing and using the updated schema correctly.

### Task 3: Local Verification & Testing

**Objective:** Ensure the API returns the exact structure requested without breaking.

- [ ] Run the FastAPI server locally (`uvicorn app.main:app --reload`).
- [ ] Execute a `GET` request to `/api/v1/inspector/profile/{id}`.
- [ ] Verify that `predict_label` accurately reflects the class with the highest probability in the `predict_proba` dictionary.
- [ ] Verify that the sum of the values in `predict_proba` roughly equals `1.0`.

---

**Note to AI Agent:** Execute these changes methodically. The goal is to make the API output tightly coupled with Scikit-Learn's native terminology.
