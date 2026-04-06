import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timezone

# Configure DB path on Modal Volume
DB_DIR = "/data/db"
DB_FILE = os.path.join(DB_DIR, "sybil_history.db")

# Fallback for local testing if /data/db doesn't exist or isn't accessible
if not os.path.exists(DB_DIR):
    DB_DIR = os.path.join(os.getcwd(), "data", "db")
    os.makedirs(DB_DIR, exist_ok=True)
    DB_FILE = os.path.join(DB_DIR, "sybil_history.db")

SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_FILE}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class InspectorHistory(Base):
    __tablename__ = "inspector_history"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    target_address = Column(String, index=True)
    predict_label = Column(String)
    confidence_score = Column(Float)
    depth_filter = Column(Integer, default=1)


class DiscoveryHistory(Base):
    __tablename__ = "discovery_history"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, index=True, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    status = Column(String, default="PROCESSING")
    start_date = Column(String)
    end_date = Column(String)
    cluster_count = Column(Integer)
    node_count = Column(Integer)
    edge_count = Column(Integer)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
