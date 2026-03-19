class SybilService:
    """
    Business logic layer for sybil discovery.

    Currently stubbed with dummy async methods; later steps will wire
    Modal/serverless execution and in-memory NetworkX graph processing.
    """

    async def start_discovery(self) -> dict:
        # Placeholder task id; replace with Modal job id later.
        return {"task_id": "dummy-task-id"}

    async def get_discovery_status(self, task_id: str) -> dict:
        # Placeholder status; replace with real persistence / job lookup later.
        return {"task_id": task_id, "status": "pending"}

