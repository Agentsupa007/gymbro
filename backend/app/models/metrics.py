from sqlalchemy import Column, String, DateTime, Float, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from app.core.database import Base

class MetricTypeEnum(str, enum.Enum):
    weight = "weight"
    body_fat = "body_fat"
    muscle_mass = "muscle_mass"
    bmi = "bmi"
    chest = "chest"
    waist = "waist"
    hips = "hips"
    biceps = "biceps"
    thighs = "thighs"

class UnitEnum(str, enum.Enum):
    kg = "kg"
    lbs = "lbs"
    percent = "%"
    cm = "cm"
    inches = "in"

class Metric(Base):
    __tablename__ = "metrics"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    metric_type = Column(Enum(MetricTypeEnum), nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(Enum(UnitEnum), nullable=False)
    recorded_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    user = relationship("User", back_populates="metrics")