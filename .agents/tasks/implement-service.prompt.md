---
description: "Integrate FastAPI Service Layer with Modal Serverless using the async spawn mechanism."
agent: "agent"
tools: ["codebase", "editFiles"]
---

# Implement Task 3: Modal Serverless Integration in Service Layer

You are an expert FastAPI developer and MLOps Engineer specializing in Serverless integrations, Clean Architecture, and non-blocking asynchronous architectures.

## Task Section

Your primary task is to update `app/services/sybil_service.py` to connect the FastAPI backend gateway to the Modal serverless platform. You will implement the Modal `.spawn()` (fire-and-forget) mechanism to prevent blocking the FastAPI event loop during heavy ML tasks, along with a polling mechanism to check task status.

## Instructions Section

### Step 1: Prepare Imports

- Open `app/services/sybil_service.py`.
- Ensure `import modal` is added at the top.
- Ensure `from app.schemas.sybil import DiscoveryRequest` is imported.

### Step 2: Implement `start_discovery`

Modify the `start_discovery(self, req: DiscoveryRequest) -> dict` method to:

1. Wrap the logic in a `try/except` block.
2. Inside `try`:
   - Lookup the Modal function: `modal_func = modal.Function.lookup("sybil-discovery-engine", "train_gae_pipeline")`.
   - Call the function asynchronously without waiting: `call = modal_func.spawn(req.model_dump())` (use `.dict()` if Pydantic v1 is used, but prefer `.model_dump()` for v2).
   - Return a dictionary: `{"task_id": call.object_id}`.
3. Inside `except Exception as e`:
   - Print a warning: `print(f"[Warning] Modal lookup/spawn failed: {e}. Using mock task.")`
   - Return a fallback mock ID for UI testing: `{"task_id": "mock-task-12345"}`.

### Step 3: Implement `get_discovery_status`

Modify the `get_discovery_status(self, task_id: str) -> dict` method to handle both mock and real Modal tasks:

1. **Mock Handling**:
   - If `"mock" in task_id`, immediately return a hardcoded dictionary with `status="COMPLETED"`, `progress=100`, and a dummy `graph_data` containing at least 2 nodes and 1 link (e.g., node 1 "HIGH_RISK", node 2 "BENIGN").
2. **Real Modal Polling** (Wrap in `try/except`):
   - Restore the call object: `call = modal.functions.FunctionCall.from_id(task_id)`.
   - Attempt to fetch the result instantly: `result = call.get(timeout=0)`.
   - If successful, return a dictionary with `task_id`, `status="COMPLETED"`, `progress=100`, and `graph_data=result`.
3. **Exception Handling for Polling**:
   - `except TimeoutError:` (This means the task is still running). Return a dictionary with `status="PROCESSING"`, `progress=45`, and `graph_data=None`.
   - `except Exception as e:` (Task crashed or invalid ID). Return a dictionary with `status="FAILED"`, `message=str(e)`, and `graph_data=None`.

## Context/Input Section

- Target file: `app/services/sybil_service.py`
- Pydantic models are assumed to be already created in `app/schemas/sybil.py` from previous steps.

## Output Section

- Directly modify `app/services/sybil_service.py` in the workspace.
- The output code must be clean, well-commented, and use proper indentation.

## Quality/Validation Section

- The server must not crash when Modal is not yet deployed (fallback to mock task must work).
- `TimeoutError` must be specifically caught so that Polling requests return `"PROCESSING"` instead of a 500 Internal Server Error.
- The method signatures must use proper Python type hinting.
