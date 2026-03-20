import uuid
import logging
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.exc import IntegrityError

from app.models.metrics import DailyMetrics, BodyMeasurement
from app.models.workout import WorkoutSession, SessionStatusEnum
from app.schemas.metrics import (
    DailyMetricsCreate, BodyMeasurementCreate, MetricsSummary,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────

def _compute_streaks(dates: list[date]) -> tuple[int, int]:
    """
    Given a list of dates, return (current_streak, longest_streak).
    Capped at last 365 days to avoid loading unbounded history.
    """
    if not dates:
        return 0, 0

    dates = sorted(set(dates))
    today = date.today()

    # Longest streak
    longest = 1
    current_run = 1
    for i in range(1, len(dates)):
        if (dates[i] - dates[i - 1]).days == 1:
            current_run += 1
            longest = max(longest, current_run)
        else:
            current_run = 1
    longest = max(longest, current_run)

    # Current streak: walk backwards from today
    date_set = set(dates)
    current_streak = 0
    check = today
    while check in date_set:
        current_streak += 1
        check -= timedelta(days=1)

    return current_streak, longest


# ─────────────────────────────────────────
# Daily Metrics
# ─────────────────────────────────────────

async def log_daily_metrics(
    db: AsyncSession,
    user_id: str,
    data: DailyMetricsCreate,
) -> DailyMetrics:
    """
    Upsert daily metrics for a given date.
    Handles race conditions via IntegrityError catch on insert.
    """
    target_date = data.date or date.today()

    # Check for existing row
    result = await db.execute(
        select(DailyMetrics).where(
            and_(
                DailyMetrics.user_id == user_id,
                DailyMetrics.date == target_date,
            )
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        # Partial update — only overwrite fields that were sent
        for field, value in data.model_dump(exclude={"date"}, exclude_none=True).items():
            setattr(existing, field, value)
        await db.commit()
        await db.refresh(existing)
        logger.info("Updated daily metrics for user=%s date=%s", user_id, target_date)
        return existing

    # Insert — catch race condition duplicate
    entry = DailyMetrics(
        id=str(uuid.uuid4()),
        user_id=user_id,
        date=target_date,
        steps=data.steps,
        calories_burned=data.calories_burned,
        calories_consumed=data.calories_consumed,
        sleep_hours=data.sleep_hours,
        water_ml=data.water_ml,
        resting_heart_rate=data.resting_heart_rate,
        notes=data.notes,
    )
    db.add(entry)
    try:
        await db.commit()
        await db.refresh(entry)
        logger.info("Created daily metrics for user=%s date=%s", user_id, target_date)
        return entry
    except IntegrityError:
        await db.rollback()
        # Concurrent insert won — fetch and update that row instead
        logger.warning("Race condition on daily_metrics insert, falling back to update")
        result = await db.execute(
            select(DailyMetrics).where(
                and_(
                    DailyMetrics.user_id == user_id,
                    DailyMetrics.date == target_date,
                )
            )
        )
        existing = result.scalar_one()
        for field, value in data.model_dump(exclude={"date"}, exclude_none=True).items():
            setattr(existing, field, value)
        await db.commit()
        await db.refresh(existing)
        return existing


async def get_daily_metrics(
    db: AsyncSession,
    user_id: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 30,
    offset: int = 0,
) -> list[DailyMetrics]:
    """
    Fetch daily metrics for a user with optional date range and pagination.
    Defaults to returning most recent 30 entries.
    """
    filters = [DailyMetrics.user_id == user_id]
    if start_date:
        filters.append(DailyMetrics.date >= start_date)
    if end_date:
        filters.append(DailyMetrics.date <= end_date)

    result = await db.execute(
        select(DailyMetrics)
        .where(and_(*filters))
        .order_by(DailyMetrics.date.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


# ─────────────────────────────────────────
# Body Measurements
# ─────────────────────────────────────────

async def log_body_measurement(
    db: AsyncSession,
    user_id: str,
    data: BodyMeasurementCreate,
) -> BodyMeasurement:
    """
    Upsert body measurement for a given date.
    """
    target_date = data.date or date.today()

    result = await db.execute(
        select(BodyMeasurement).where(
            and_(
                BodyMeasurement.user_id == user_id,
                BodyMeasurement.date == target_date,
            )
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        for field, value in data.model_dump(exclude={"date"}, exclude_none=True).items():
            setattr(existing, field, value)
        await db.commit()
        await db.refresh(existing)
        logger.info("Updated body measurement for user=%s date=%s", user_id, target_date)
        return existing

    entry = BodyMeasurement(
        id=str(uuid.uuid4()),
        user_id=user_id,
        date=target_date,
        weight_kg=data.weight_kg,
        body_fat_pct=data.body_fat_pct,
        muscle_mass_kg=data.muscle_mass_kg,
        chest_cm=data.chest_cm,
        waist_cm=data.waist_cm,
        hips_cm=data.hips_cm,
        notes=data.notes,
    )
    db.add(entry)
    try:
        await db.commit()
        await db.refresh(entry)
        logger.info("Created body measurement for user=%s date=%s", user_id, target_date)
        return entry
    except IntegrityError:
        await db.rollback()
        logger.warning("Race condition on body_measurements insert, falling back to update")
        result = await db.execute(
            select(BodyMeasurement).where(
                and_(
                    BodyMeasurement.user_id == user_id,
                    BodyMeasurement.date == target_date,
                )
            )
        )
        existing = result.scalar_one()
        for field, value in data.model_dump(exclude={"date"}, exclude_none=True).items():
            setattr(existing, field, value)
        await db.commit()
        await db.refresh(existing)
        return existing


# ─────────────────────────────────────────
# Summary
# ─────────────────────────────────────────

async def get_metrics_summary(
    db: AsyncSession,
    user_id: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> MetricsSummary:
    """
    Aggregate metrics for the dashboard summary.
    Defaults to last 30 days if no range provided.
    """
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    # Convert to datetime for index-safe comparisons
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    daily_filters = [
        DailyMetrics.user_id == user_id,
        DailyMetrics.date >= start_date,
        DailyMetrics.date <= end_date,
    ]
    body_filters = [
        BodyMeasurement.user_id == user_id,
        BodyMeasurement.date >= start_date,
        BodyMeasurement.date <= end_date,
    ]

    # ── Aggregates ──
    agg_result = await db.execute(
        select(
            func.avg(DailyMetrics.steps).label("avg_steps"),
            func.avg(DailyMetrics.sleep_hours).label("avg_sleep_hours"),
            func.avg(DailyMetrics.calories_burned).label("avg_calories_burned"),
            func.avg(DailyMetrics.calories_consumed).label("avg_calories_consumed"),
            func.avg(DailyMetrics.resting_heart_rate).label("avg_resting_heart_rate"),
            func.sum(DailyMetrics.water_ml).label("total_water_ml"),
            func.count(DailyMetrics.id).label("days_logged"),
        ).where(and_(*daily_filters))
    )
    agg = agg_result.one()

    # ── Latest daily snapshot ──
    latest_daily_result = await db.execute(
        select(DailyMetrics)
        .where(and_(*daily_filters))
        .order_by(DailyMetrics.date.desc())
        .limit(1)
    )
    latest_daily = latest_daily_result.scalar_one_or_none()

    # ── Latest body measurement ──
    latest_body_result = await db.execute(
        select(BodyMeasurement)
        .where(and_(*body_filters))
        .order_by(BodyMeasurement.date.desc())
        .limit(1)
    )
    latest_body = latest_body_result.scalar_one_or_none()

    # ── Oldest body measurement with weight (for trend) ──
    oldest_body_result = await db.execute(
        select(BodyMeasurement)
        .where(and_(*body_filters, BodyMeasurement.weight_kg.isnot(None)))
        .order_by(BodyMeasurement.date.asc())
        .limit(1)
    )
    oldest_body = oldest_body_result.scalar_one_or_none()

    # ── Weight change: only meaningful if two distinct dates exist ──
    weight_change = None
    if (
        latest_body and oldest_body
        and latest_body.weight_kg and oldest_body.weight_kg
        and latest_body.date != oldest_body.date      # ✅ compare dates, not IDs
    ):
        weight_change = round(latest_body.weight_kg - oldest_body.weight_kg, 2)

    # ── Workout count — datetime range, index-safe ──
    workout_result = await db.execute(
        select(func.count(WorkoutSession.id)).where(
            and_(
                WorkoutSession.user_id == user_id,
                WorkoutSession.status == SessionStatusEnum.completed,
                WorkoutSession.started_at >= start_dt,   # ✅ datetime, not func.date()
                WorkoutSession.started_at <= end_dt,
            )
        )
    )
    workout_count = workout_result.scalar() or 0

    # ── Streak — capped at last 365 days to avoid unbounded load ──
    streak_cutoff = date.today() - timedelta(days=365)
    all_dates_result = await db.execute(
        select(DailyMetrics.date).where(
            and_(
                DailyMetrics.user_id == user_id,
                DailyMetrics.date >= streak_cutoff,      # ✅ bounded
            )
        )
    )
    all_dates = [row[0] for row in all_dates_result.all()]
    current_streak, longest_streak = _compute_streaks(all_dates)

    return MetricsSummary(
        avg_steps=round(agg.avg_steps, 1) if agg.avg_steps else None,
        avg_sleep_hours=round(agg.avg_sleep_hours, 2) if agg.avg_sleep_hours else None,
        avg_calories_burned=round(agg.avg_calories_burned, 1) if agg.avg_calories_burned else None,
        avg_calories_consumed=round(agg.avg_calories_consumed, 1) if agg.avg_calories_consumed else None,
        avg_resting_heart_rate=round(agg.avg_resting_heart_rate, 1) if agg.avg_resting_heart_rate else None,
        total_water_ml=int(agg.total_water_ml) if agg.total_water_ml else None,
        latest_steps=latest_daily.steps if latest_daily else None,
        latest_calories_burned=latest_daily.calories_burned if latest_daily else None,
        latest_calories_consumed=latest_daily.calories_consumed if latest_daily else None,
        latest_weight_kg=latest_body.weight_kg if latest_body else None,
        latest_body_fat_pct=latest_body.body_fat_pct if latest_body else None,
        weight_change_kg=weight_change,
        workout_count=workout_count,
        current_streak=current_streak,
        longest_streak=longest_streak,
        days_logged=agg.days_logged or 0,
    )