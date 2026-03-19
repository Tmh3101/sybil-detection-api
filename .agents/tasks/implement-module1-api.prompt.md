---
description: "Implement Pydantic Schemas and integrate the Modal Serverless (Spawn) calling mechanism into the Service Layer for Module 1 (Sybil Discovery)."
agent: "agent"
tools: ["codebase", "editFiles"]
---

# Implement Module 1 API: Schemas & Modal Integration

You are an expert in FastAPI and MLOps. The current system already has a basic skeleton. Your task is to materialize the API Contract for Module 1 (Batch Processing) by defining Pydantic schemas and updating the Service layer.

## Instructions

### Step 1: Define Pydantic Schemas

Modify or create the file `app/schemas/sybil.py` and define the following models:

1. `TimeRange`: contains `start_date` (str) and `end_date` (str).
2. `DiscoveryRequest`: contains `time_range` (TimeRange) and `max_nodes` (int, default=2000).
3. `NodeSchema`: id (str), label (str), cluster_id (int), risk_score (float), attributes (dict).
4. `LinkSchema`: source (str), target (str), edge_type (str), weight (float).
5. `GraphDataSchema`: nodes (list[NodeSchema]), links (list[LinkSchema]).
6. `DiscoveryStatusResponse`: task_id (str), status (str: "PROCESSING", "COMPLETED", "FAILED"), progress (int), current_step (str), graph_data (Optional[GraphDataSchema]), message (Optional[str]).

### Step 2: Update the Router (`app/api/v1/endpoints/sybil.py`)

- Import the newly created schemas.
- Update the `start_sybil_discovery` function to accept the parameter `req: DiscoveryRequest`.
- Update both endpoints to use `response_model=DiscoveryStatusResponse` (or a standard dictionary format).

### Step 3: Update the Service Layer (`app/services/sybil_service.py`)

Update the `SybilService` class to integrate the Modal SDK (`import modal`):

1. **In `start_discovery(self, req: DiscoveryRequest)`:**
   - Use a `try/except` block to lookup the Modal function: `modal_func = modal.Function.lookup("sybil-discovery-engine", "train_gae_pipeline")`.
   - Call the function asynchronously using `.spawn(req.model_dump())`.
   - Return a dictionary containing the `task_id` (which is `call.object_id`).
   - _(Note: If the lookup fails because the Modal app hasn't been deployed yet, catch the Exception and return a mock `task_id` such as "mock-task-123" to test the flow)._

2. **In `get_discovery_status(self, task_id: str)`:**
   - If the `task_id` contains the word "mock", return Mock data directly (status COMPLETED, with a few dummy nodes/links) so the Frontend can test immediately.
   - Otherwise, restore the call: `call = modal.functions.FunctionCall.from_id(task_id)`.
   - Try to retrieve the result: `result = call.get(timeout=0)`.
   - If successful, return `status="COMPLETED"`, `progress=100`, and inject the result into `graph_data`.
   - If a `TimeoutError` exception is raised, catch it safely and return `status="PROCESSING"`, `progress=45`.
   - For any other exceptions, return `status="FAILED"`.

## Constraints & Standards

- Use modern Python Type Hints (e.g., `dict` and `list` instead of `Dict` and `List` for Python 3.9+).
- Ensure `TimeoutError` is handled safely so the server does not crash while Modal is still processing the job.
