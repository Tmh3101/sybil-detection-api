from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_sybil_service
from app.schemas.sybil import DiscoveryRequest, DiscoveryStatusResponse
from app.services.sybil_service import SybilService
from app.database import get_db, DiscoveryHistory

router = APIRouter()


@router.post("/discovery/start", response_model=DiscoveryStatusResponse)
async def start_sybil_discovery(
    req: DiscoveryRequest,
    sybil_service: SybilService = Depends(get_sybil_service),
    db: Session = Depends(get_db),
):
    """
    Dummy endpoint to kick off discovery.

    In the next steps this will enqueue a heavy job to Modal and return a task id.
    """
    print(f"DiscoveryRequest: {req}")
    res = await sybil_service.start_discovery(req=req)

    try:
        start_date = req.time_range.start_date
        end_date = req.time_range.end_date

        history_record = DiscoveryHistory(
            task_id=res.task_id,
            start_date=start_date,
            end_date=end_date,
            cluster_count=0,
            node_count=0,
            edge_count=0,
        )

        print(f"discovery_history_record: {history_record}")

        db.add(history_record)
        db.commit()
    except Exception as db_err:
        print(f"Failed to save discovery history: {db_err}")
        db.rollback()

    return res


@router.get(
    "/discovery/status/{task_id}",
    response_model=DiscoveryStatusResponse,
)
async def discovery_status(
    task_id: str,
    sybil_service: SybilService = Depends(get_sybil_service),
    db: Session = Depends(get_db),
):
    """Dummy endpoint returning discovery status by task id."""
    res = await sybil_service.get_discovery_status(task_id=task_id)

    # Update history record if task is completed and record exists
    if res.status == "COMPLETED" and res.graph_data:
        try:
            history_record = (
                db.query(DiscoveryHistory)
                .filter(DiscoveryHistory.task_id == task_id)
                .first()
            )
            if history_record and history_record.status == "PROCESSING":
                history_record.cluster_count = (
                    res.graph_data.cluster_count if res.graph_data.cluster_count else 0
                )
                history_record.node_count = (
                    len(res.graph_data.nodes) if res.graph_data.nodes else 0
                )
                history_record.edge_count = (
                    len(res.graph_data.links) if res.graph_data.links else 0
                )
                history_record.status = "COMPLETED"
                db.commit()
                print(f"Updated discovery history for task {task_id}")
        except Exception as db_err:
            print(f"Failed to update discovery history: {db_err}")
            db.rollback()

    return res
