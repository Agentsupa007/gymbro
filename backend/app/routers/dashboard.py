"""
routers/dashboard.py

Single endpoint that powers the entire Dashboard page.
Returns everything in one call so the frontend doesn't need to fan out.

GET /dashboard/summary
  → today's metrics snapshot
  → progress stats (streak, workouts this month, weight, weight change)
  → recent sessions (last 3 completed)
  → latest AI tip (last assistant message from most recent conversation)
"""

import logging
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, asc

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.metrics import DailyMetrics, BodyMeasurement
from app.models.workout import WorkoutSession, SessionStatusEnum, SessionExercise
from app.models.memory import Conversation, Message, MessageRoleEnum
from app.services.metrics_service import get_metrics_summary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
logger = logging.getLogger(__name__)


@router.get("/summary")
async def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Assembles the full dashboard payload for the authenticated user.
    Every section is individually try/catch-ed so a failure in one
    section never breaks the whole response.
    """
    user_id = str(current_user.id)
    today = date.today()
    payload = {}

    # ── Today's Metrics Snapshot ──────────────────────────────────────────────
    try:
        result = await db.execute(
            select(DailyMetrics).where(
                and_(
                    DailyMetrics.user_id == user_id,
                    DailyMetrics.date == today,
                )
            )
        )
        today_metrics = result.scalar_one_or_none()

        payload["today"] = {
            "steps":           today_metrics.steps if today_metrics else None,
            "calories_burned": today_metrics.calories_burned if today_metrics else None,
            "sleep_hours":     today_metrics.sleep_hours if today_metrics else None,
            "water_ml":        today_metrics.water_ml if today_metrics else None,
        }
    except Exception as e:
        logger.error(f"Dashboard: today metrics failed for user {user_id}: {e}")
        payload["today"] = {"steps": None, "calories_burned": None, "sleep_hours": None, "water_ml": None}

    # ── Progress Stats (last 30 days) ─────────────────────────────────────────
    try:
        summary = await get_metrics_summary(db=db, user_id=user_id)

        # Workouts this calendar month (not just last 30 days)
        month_start = today.replace(day=1)
        month_start_dt = datetime.combine(month_start, datetime.min.time())
        month_end_dt = datetime.combine(today, datetime.max.time())

        month_workout_result = await db.execute(
            select(WorkoutSession).where(
                and_(
                    WorkoutSession.user_id == user_id,
                    WorkoutSession.status == SessionStatusEnum.completed,
                    WorkoutSession.started_at >= month_start_dt,
                    WorkoutSession.started_at <= month_end_dt,
                )
            )
        )
        workouts_this_month = len(month_workout_result.scalars().all())

        payload["progress"] = {
            "current_streak":      summary.current_streak,
            "longest_streak":      summary.longest_streak,
            "workouts_this_month": workouts_this_month,
            "weight_kg":           summary.latest_weight_kg,
            "weight_change_kg":    summary.weight_change_kg,
        }
    except Exception as e:
        logger.error(f"Dashboard: progress stats failed for user {user_id}: {e}")
        payload["progress"] = {
            "current_streak": 0, "longest_streak": 0,
            "workouts_this_month": 0, "weight_kg": None, "weight_change_kg": None,
        }

    # ── Recent Sessions (last 3 completed) ────────────────────────────────────
    try:
        sessions_result = await db.execute(
            select(WorkoutSession)
            .where(
                and_(
                    WorkoutSession.user_id == user_id,
                    WorkoutSession.status == SessionStatusEnum.completed,
                )
            )
            .order_by(desc(WorkoutSession.started_at))
            .limit(3)
        )
        sessions = sessions_result.scalars().all()

        recent_sessions = []
        for s in sessions:
            # Get exercise count for this session
            ex_result = await db.execute(
                select(SessionExercise).where(SessionExercise.session_id == s.id)
            )
            exercise_count = len(ex_result.scalars().all())

            recent_sessions.append({
                "id":             str(s.id),
                "name":           s.name or "Workout",
                "started_at":     s.started_at.isoformat() if s.started_at else None,
                "duration_mins":  s.duration_minutes,
                "exercise_count": exercise_count,
            })

        payload["recent_sessions"] = recent_sessions
    except Exception as e:
        logger.error(f"Dashboard: recent sessions failed for user {user_id}: {e}")
        payload["recent_sessions"] = []

    # ── Latest AI Tip ─────────────────────────────────────────────────────────
    try:
        # Most recent conversation
        convo_result = await db.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(desc(Conversation.updated_at))
            .limit(1)
        )
        convo = convo_result.scalar_one_or_none()

        latest_tip = None
        if convo:
            msg_result = await db.execute(
                select(Message)
                .where(
                    and_(
                        Message.conversation_id == convo.id,
                        Message.role == MessageRoleEnum.assistant,
                    )
                )
                .order_by(desc(Message.created_at))
                .limit(1)
            )
            last_msg = msg_result.scalar_one_or_none()
            if last_msg:
                # Trim to a readable tip length
                tip = last_msg.content.strip()
                latest_tip = tip[:280] + "…" if len(tip) > 280 else tip

        payload["latest_tip"] = latest_tip
    except Exception as e:
        logger.error(f"Dashboard: latest tip failed for user {user_id}: {e}")
        payload["latest_tip"] = None

    return payload