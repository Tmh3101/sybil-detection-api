# Implementation Plan: Standardize Backend Graph API (Phase 1)

## Overview

This plan focuses exclusively on refactoring the FastAPI backend (running on Modal) to unify the graph data schema returned by Module 1 (Discovery) and Module 2 (Inspector). The goal is to establish a "Golden Schema" for Nodes and Edges so that the frontend can consume them predictably without hacky workarounds.

**Core Objectives:**

1. **Clean Labels:** Strip numeric prefixes (e.g., `0_BENIGN` -> `BENIGN`) from all risk labels and classifications across both modules.
2. **Unify Nodes:** Ensure `local_graph.nodes` in Module 2 strictly contains `label`, `risk_score`, `cluster_id` (default to 0), and a fully populated `attributes` dictionary (`follower_count`, `post_count`, `trust_score`, `reason`), matching Module 1 exactly.
3. **Unify Edges:** Guarantee all edges/links in both modules use the `edge_type` key.

## AI Agent Execution Directives

**CRITICAL:** You are instructed to execute these tasks sequentially. **After completing each task, you MUST open this plan document and update the checklist below by changing `[ ]` to `[x]` before proceeding to the next task.**

## Scope & File Structure

- **Target File:** `modal_worker/modal_app.py` (or the specific file handling the FastAPI endpoints and data extraction logic).

## Step-by-Step Tasks & Checklist

### [x] Task 1: Implement Label Sanitization Logic

- **Action:** Locate or create a helper function/logic in the backend to strip numeric prefixes from risk labels (e.g., transforming `"0_BENIGN"` into `"BENIGN"`, `"3_MALICIOUS"` into `"MALICIOUS"`).
- **Update:** Apply this sanitization to the `analysis.classification` field in the Module 2 response payload.
- **Commit:** "refactor(backend): add label sanitization to strip numeric prefixes"

### [x] Task 2: Standardize Module 1 (Discovery) Output

- **Action:** Locate the endpoint logic for Module 1 (`/api/v1/sybil/discovery/status/{task_id}` or the GAE task result builder).
- **Node Update:** Ensure the `label` field assigned to each node in the `nodes` array uses the sanitized string (no "0\_" prefix).
- **Edge Update:** Verify that the relationship key is explicitly set to `edge_type` (not `type`).
- **Commit:** "refactor(backend): standardize discovery nodes label and edge_type"

### [x] Task 3: Overhaul Module 2 (Inspector) Local Graph Extraction

- **Action:** Locate the endpoint logic for Module 2 (`/api/v1/inspector/profile/{profile_id}`) and specifically the part that builds the `local_graph`.
- **Node Update:** Modify the node extraction loop. For every neighbor node, you MUST now inject:
  - `label` (Sanitized, e.g., "BENIGN").
  - `risk_score` (Float).
  - `cluster_id` (Integer, default to 0 if clustering is not applied to local graph).
- **Attributes Update:** Ensure the `attributes` dict for these neighbor nodes includes `follower_count`, `post_count`, `trust_score`, and `reason` (can be `None` or empty string if not computed, but the keys must exist).
- **Edge Update:** Ensure the edges in `local_graph.links` use the `edge_type` key.
- **Commit:** "refactor(backend): overhaul inspector local_graph to match golden schema"

## Plan Review Loop

After writing the complete plan:

1. Dispatch a single plan-document-reviewer subagent with precisely crafted review context.
2. If ❌ Issues Found: fix the issues, re-dispatch reviewer for the whole plan.
3. If ✅ Approved: proceed to execution handoff.

````

---

### Lệnh để giao việc cho AI Agent (Backend Execution Prompt)

Sau khi lưu file Plan trên, bạn hãy gửi prompt dưới đây cho AI Agent (Cursor/Copilot) để nó bắt đầu sửa code Python của Backend:

```markdown
I have created a detailed backend implementation plan at `docs/superpowers/plans/2026-03-25-backend-api-standardization.md`.

I choose Option 2: **Inline Execution**.

Please act as an expert Python/FastAPI Backend Engineer. Read the plan document carefully. You must execute the tasks sequentially from Task 1 to Task 3 on our FastAPI backend code (`modal_app.py` or equivalent).

**CRITICAL RULES FOR YOU:**

1. Execute ONE task at a time.
2. After writing/modifying the python code for a task, you MUST edit the plan markdown file to change the corresponding `[ ]` to `[x]`.
3. Provide a brief summary of the changes you made for that task, and then automatically proceed to the next task until all 3 tasks are marked as `[x]`.

Begin with Task 1 now. Focus ONLY on the backend code.
````
