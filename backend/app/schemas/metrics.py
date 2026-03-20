from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional
from datetime import date as Date, datetime


def round2(v: Optional[float]) -> Optional[float]:
    return round(v, 2) if v is not None else None


# ─────────────────────────────────────────
# Daily Metrics
# ─────────────────────────────────────────

class DailyMetricsCreate(BaseModel):
    date: Optional[Date] = Field(default_factory=Date.today)

    steps: Optional[int] = Field(None, ge=0, le=100_000)
    calories_burned: Optional[int] = Field(None, ge=0, le=10_000)
    calories_consumed: Optional[int] = Field(None, ge=0, le=20_000)
    sleep_hours: Optional[float] = Field(None, ge=0, le=24)
    water_ml: Optional[int] = Field(None, ge=0, le=20_000)
    resting_heart_rate: Optional[int] = Field(None, ge=20, le=250)
    notes: Optional[str] = Field(None, max_length=500)

    @field_validator("sleep_hours", mode="before")
    @classmethod
    def round_sleep(cls, v):
        return round2(v)

    @model_validator(mode="after")
    def require_at_least_one_metric(self):
        metric_fields = [
            self.steps, self.calories_burned, self.calories_consumed,
            self.sleep_hours, self.water_ml, self.resting_heart_rate,
        ]
        if all(v is None for v in metric_fields):
            raise ValueError(
                "At least one metric field must be provided "
                "(steps, calories_burned, calories_consumed, "
                "sleep_hours, water_ml, or resting_heart_rate)."
            )
        return self


class DailyMetricsResponse(BaseModel):
    id: str          # ✅ UUID string, not int
    user_id: str     # ✅ UUID string, not int
    date: Date
    steps: Optional[int]
    calories_burned: Optional[int]
    calories_consumed: Optional[int]
    sleep_hours: Optional[float]
    water_ml: Optional[int]
    resting_heart_rate: Optional[int]
    notes: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────
# Body Measurements
# ─────────────────────────────────────────

class BodyMeasurementCreate(BaseModel):
    date: Optional[Date] = Field(default_factory=Date.today)

    weight_kg: Optional[float] = Field(None, gt=0, le=500)
    body_fat_pct: Optional[float] = Field(None, ge=0, le=100)
    muscle_mass_kg: Optional[float] = Field(None, ge=0, le=500)
    chest_cm: Optional[float] = Field(None, ge=0, le=300)
    waist_cm: Optional[float] = Field(None, ge=0, le=300)
    hips_cm: Optional[float] = Field(None, ge=0, le=300)
    notes: Optional[str] = Field(None, max_length=500)

    @field_validator("weight_kg", "body_fat_pct", "muscle_mass_kg",
                     "chest_cm", "waist_cm", "hips_cm", mode="before")
    @classmethod
    def round_floats(cls, v):
        return round2(v)

    @model_validator(mode="after")
    def require_at_least_one_measurement(self):
        measurement_fields = [
            self.weight_kg, self.body_fat_pct, self.muscle_mass_kg,
            self.chest_cm, self.waist_cm, self.hips_cm,
        ]
        if all(v is None for v in measurement_fields):
            raise ValueError(
                "At least one measurement field must be provided "
                "(weight_kg, body_fat_pct, muscle_mass_kg, "
                "chest_cm, waist_cm, or hips_cm)."
            )
        return self


class BodyMeasurementResponse(BaseModel):
    id: str          # ✅ UUID string
    user_id: str     # ✅ UUID string
    date: Date
    weight_kg: Optional[float]
    body_fat_pct: Optional[float]
    muscle_mass_kg: Optional[float]
    chest_cm: Optional[float]
    waist_cm: Optional[float]
    hips_cm: Optional[float]
    notes: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────
# Summary — all fields now declared
# ─────────────────────────────────────────

class MetricsSummary(BaseModel):
    # Averages
    avg_steps: Optional[float]
    avg_sleep_hours: Optional[float]
    avg_calories_burned: Optional[float]
    avg_calories_consumed: Optional[float]       # ✅ added
    avg_resting_heart_rate: Optional[float]
    total_water_ml: Optional[int]

    # Latest daily snapshot
    latest_steps: Optional[int]                  # ✅ added
    latest_calories_burned: Optional[int]        # ✅ added
    latest_calories_consumed: Optional[int]      # ✅ added

    # Latest body measurements
    latest_weight_kg: Optional[float]
    latest_body_fat_pct: Optional[float]

    # Weight trend
    weight_change_kg: Optional[float]

    # Workout activity
    workout_count: int                           # ✅ added

    # Streaks
    current_streak: int                          # ✅ added
    longest_streak: int                          # ✅ added

    # Coverage
    days_logged: int