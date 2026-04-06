from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db, InspectorHistory, DiscoveryHistory

router = APIRouter()


@router.get("/inspector")
def get_inspector_history(db: Session = Depends(get_db)):
    records = (
        db.query(InspectorHistory)
        .order_by(InspectorHistory.timestamp.desc())
        .limit(50)
        .all()
    )
    return records


@router.get("/discovery")
def get_discovery_history(db: Session = Depends(get_db)):
    records = (
        db.query(DiscoveryHistory)
        .order_by(DiscoveryHistory.timestamp.desc())
        .limit(10)
        .all()
    )
    return records
