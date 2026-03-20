from sqlalchemy import (
    Column, String, DateTime, Date, Float, Integer,
    Text, ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.core.database import Base


class DailyMetrics(Base):
    __tablename__ = "daily_metrics"

    __table_args__ = (
        # One entry per user per day — enforced at DB level
        UniqueConstraint("user_id", "date", name="uq_daily_metrics_user_date"),
        Index("ix_daily_metrics_user_date", "user_id", "date"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)

    steps = Column(Integer, nullable=True)
    calories_burned = Column(Integer, nullable=True)
    calories_consumed = Column(Integer, nullable=True)
    sleep_hours = Column(Float, nullable=True)
    water_ml = Column(Integer, nullable=True)
    resting_heart_rate = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="daily_metrics")


class BodyMeasurement(Base):
    __tablename__ = "body_measurements"

    __table_args__ = (
        # One measurement entry per user per day
        UniqueConstraint("user_id", "date", name="uq_body_measurements_user_date"),
        Index("ix_body_measurements_user_date", "user_id", "date"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)

    weight_kg = Column(Float, nullable=True)
    body_fat_pct = Column(Float, nullable=True)
    muscle_mass_kg = Column(Float, nullable=True)
    chest_cm = Column(Float, nullable=True)
    waist_cm = Column(Float, nullable=True)
    hips_cm = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="body_measurements")