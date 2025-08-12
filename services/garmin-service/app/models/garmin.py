from sqlalchemy import Column, String, Integer, DateTime, Text, Numeric, JSON, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.core.database import Base
import uuid

class GarminActivity(Base):
    __tablename__ = "garmin_activities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    activity_id = Column(String(100), nullable=False)
    activity_type = Column(String(100))
    activity_name = Column(String(200))
    start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    duration_seconds = Column(Integer)
    distance_meters = Column(Numeric(10, 2))
    calories = Column(Integer)
    avg_heart_rate = Column(Integer)
    max_heart_rate = Column(Integer)
    raw_data = Column(JSON)
    processed_at = Column(DateTime(timezone=True), default=func.now())

class GarminHealthMetric(Base):
    __tablename__ = "garmin_health_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    metric_type = Column(String(50), nullable=False, index=True)
    recorded_date = Column(DateTime(timezone=True), nullable=False, index=True)
    metric_data = Column(JSON, nullable=False)
    processed_at = Column(DateTime(timezone=True), default=func.now())