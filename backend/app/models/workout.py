from sqlalchemy import Column, String, DateTime, Integer, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.core.database import Base


class Workout(Base):
    __tablename__ = "workouts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    notes = Column(Text)
    duration_minutes = Column(Integer)
    workout_date = Column(DateTime(timezone=True), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="workouts")
    exercises = relationship("Exercise", back_populates="workout", cascade="all, delete-orphan")


class Exercise(Base):
    __tablename__ = "exercises"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workout_id = Column(String, ForeignKey("workouts.id"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    sets = Column(Integer)
    reps = Column(Integer)
    weight_kg = Column(Float)
    duration_seconds = Column(Integer)
    notes = Column(Text)
    order_index = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    workout = relationship("Workout", back_populates="exercises")