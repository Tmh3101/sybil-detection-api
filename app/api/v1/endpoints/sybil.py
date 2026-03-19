from fastapi import APIRouter, Depends

from app.api.dependencies import get_sybil_service
from app.schemas.sybil import DiscoveryRequest, DiscoveryStatusResponse
from app.services.sybil_service import SybilService

router = APIRouter(tags=["sybil"])


@router.post("/sybil/discovery/start", response_model=DiscoveryStatusResponse)
async def start_sybil_discovery(
    req: DiscoveryRequest,
    sybil_service: SybilService = Depends(get_sybil_service),
):
    """
    Dummy endpoint to kick off discovery.

    In the next steps this will enqueue a heavy job to Modal and return a task id.
    """
    return await sybil_service.start_discovery(req=req)


@router.get(
    "/sybil/discovery/status/{task_id}",
    response_model=DiscoveryStatusResponse,
)
async def discovery_status(
    task_id: str,
    sybil_service: SybilService = Depends(get_sybil_service),
):
    """Dummy endpoint returning discovery status by task id."""
    return await sybil_service.get_discovery_status(task_id=task_id)

