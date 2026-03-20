from __future__ import annotations

from typing import Any

from app.schemas.sybil import DiscoveryRequest

try:
    # Optional at dev-time; production expects `modal` installed and deployed.
    import modal  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    modal = None  # type: ignore


class SybilService:
    """Business logic layer for sybil discovery."""

    async def start_discovery(self, req: DiscoveryRequest) -> dict:
        """
        Start Module 1 discovery.

        Spawns the Modal job and returns a task id that can be used to poll
        for status and (eventually) graph output.
        """

        # Pydantic v2 uses `model_dump()`, but we keep a fallback for safety.
        payload = req.model_dump() if hasattr(req, "model_dump") else req.dict()

        try:
            if modal is None:
                raise RuntimeError("Modal SDK not available")

            modal_func = modal.Function.from_name(
                "sybil-discovery-engine",
                "train_gae_pipeline",
            )
            call = await modal_func.spawn.aio(payload)
            return {"task_id": call.object_id}
        except Exception as e:
            # If the lookup fails because the Modal app hasn't been deployed yet,
            # catch the exception and return a mock task id to test the flow.
            print(f"[Warning] Modal lookup/spawn failed: {e}. Using mock task.")
            return {"task_id": "mock-task-12345"}

    async def get_discovery_status(self, task_id: str) -> dict:
        """
        Poll Module 1 discovery status by task id.

        Returns a `DiscoveryStatusResponse`-shaped dict:
        - PROCESSING while the job runs
        - COMPLETED when graph data is ready
        - FAILED on unexpected errors
        """

        if "mock" in task_id:
            # Frontend-friendly completed payload for immediate testing.
            return {
                "task_id": task_id,
                "status": "COMPLETED",
                "progress": 100,
                "current_step": "FINALIZE_GRAPH",
                "graph_data": {
                    "nodes": [
                        {
                            "id": "node-1",
                            "label": "HIGH_RISK",
                            "cluster_id": 0,
                            "risk_score": 0.92,
                            "attributes": {"address": "0xHIGH"},
                        },
                        {
                            "id": "node-2",
                            "label": "BENIGN",
                            "cluster_id": 0,
                            "risk_score": 0.05,
                            "attributes": {"address": "0xBENIGN"},
                        },
                    ],
                    "links": [
                        {
                            "source": "node-1",
                            "target": "node-2",
                            "edge_type": "interaction",
                            "weight": 0.7,
                        },
                    ],
                },
                "message": None,
            }

        if modal is None:
            return {
                "task_id": task_id,
                "status": "FAILED",
                "progress": 0,
                "current_step": "MODAL_UNAVAILABLE",
                "graph_data": None,
                "message": "Modal SDK not available in this environment.",
            }

        try:
            call = modal.FunctionCall.from_id(task_id)

            # Try to retrieve the result immediately; if Modal is still running
            # the call will raise a TimeoutError.
            result: Any = await call.get.aio(timeout=0)

            return {
                "task_id": task_id,
                "status": "COMPLETED",
                "progress": 100,
                "current_step": "COMPLETE",
                "graph_data": result,
                "message": None,
            }
        except Exception as exc:
            # Modal's aio get raises asyncio.TimeoutError (or similar) on timeout.
            # We check the class name or type to keep it robust.
            if exc.__class__.__name__ == "TimeoutError":
                return {
                    "task_id": task_id,
                    "status": "PROCESSING",
                    "progress": 45,
                    "current_step": "RUNNING",
                    "graph_data": None,
                    "message": None,
                }
            return {
                "task_id": task_id,
                "status": "FAILED",
                "progress": 0,
                "current_step": "ERROR",
                "graph_data": None,
                "message": str(exc),
            }

