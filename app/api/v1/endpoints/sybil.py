from fastapi import APIRouter, Depends

from app.api.dependencies import get_sybil_service
from app.services.sybil_service import SybilService

router = APIRouter(tags=["sybil"])


@router.post("/sybil/discovery/start")
async def start_sybil_discovery(
    sybil_service: SybilService = Depends(get_sybil_service),
):
    """
    Dummy endpoint to kick off discovery.

    In the next steps this will enqueue a heavy job to Modal and return a task id.
    """
    result = await sybil_service.start_discovery()
    return {"task_id": result["task_id"]}


@router.get("/sybil/discovery/status/{task_id}")
async def discovery_status(
    task_id: str,
    sybil_service: SybilService = Depends(get_sybil_service),
):
    """Dummy endpoint returning discovery status by task id."""
    return await sybil_service.get_discovery_status(task_id=task_id)

