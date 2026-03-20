from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date as Date
from typing import Optional
import logging

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.metrics import (
    DailyMetricsCreate,
    DailyMetricsResponse,
    BodyMeasurementCreate,
    BodyMeasurementResponse,
    MetricsSummary,
)
from app.services import metrics_service

router = APIRouter(prefix="/metrics", tags=["metrics"])
logger = logging.getLogger(__name__)


# ─── Daily Metrics ────────────────────────────────────────────────────────────

@router.post(
    "/daily",
    response_model=DailyMetricsResponse,
    status_code=status.HTTP_200_OK,
    summary="Log or update daily metrics",
    description=(
        "Upsert daily metrics for the authenticated user. "
        "If an entry already exists for the given date, it will be updated. "
        "Defaults to today if no date is provided. "
        "At least one metric field must be included in the request."
    ),
)
async def log_daily_metrics(
    data: DailyMetricsCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await metrics_service.log_daily_metrics(db, current_user.id, data)
    except Exception as e:
        logger.error("Failed to log daily metrics for user=%s: %s", current_user.id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save daily metrics.",
        )


@router.get(
    "/daily",
    response_model=list[DailyMetricsResponse],
    summary="Get daily metrics",
    description=(
        "Returns paginated daily metrics for the authenticated user, "
        "ordered by date descending. Optionally filter by date range. "
        "Defaults to the most recent 30 entries."
    ),
)
async def get_daily_metrics(
    start_date: Optional[Date] = Query(None, description="Filter from this date (inclusive)"),
    end_date: Optional[Date] = Query(None, description="Filter to this date (inclusive)"),
    limit: int = Query(30, ge=1, le=365, description="Max entries to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="start_date must be before or equal to end_date.",
        )
    return await metrics_service.get_daily_metrics(
        db,
        current_user.id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )


# ─── Body Measurements ────────────────────────────────────────────────────────

@router.post(
    "/body",
    response_model=BodyMeasurementResponse,
    status_code=status.HTTP_200_OK,
    summary="Log or update body measurements",
    description=(
        "Upsert body measurements for the authenticated user. "
        "If an entry already exists for the given date, it will be updated. "
        "Defaults to today if no date is provided. "
        "At least one measurement field must be included in the request."
    ),
)
async def log_body_measurement(
    data: BodyMeasurementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await metrics_service.log_body_measurement(db, current_user.id, data)
    except Exception as e:
        logger.error("Failed to log body measurement for user=%s: %s", current_user.id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save body measurements.",
        )


# ─── Summary ──────────────────────────────────────────────────────────────────

@router.get(
    "/summary",
    response_model=MetricsSummary,
    summary="Get aggregated metrics summary",
    description=(
        "Returns aggregated metrics for the authenticated user over a date range. "
        "Includes averages, latest snapshots, weight trend, workout count, and streaks. "
        "Defaults to the last 30 days if no range is provided."
    ),
)
async def get_metrics_summary(
    start_date: Optional[Date] = Query(None, description="Start of summary range"),
    end_date: Optional[Date] = Query(None, description="End of summary range"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="start_date must be before or equal to end_date.",
        )
    return await metrics_service.get_metrics_summary(
        db,
        current_user.id,
        start_date=start_date,
        end_date=end_date,
    )