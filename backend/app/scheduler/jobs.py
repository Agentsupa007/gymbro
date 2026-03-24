"""
scheduler/jobs.py

APScheduler configuration for the weekly summary pipeline.

Registers a cron job that runs every Sunday at 23:59 (server local time).
On each run, iterates all active users and generates their weekly summary.
"""

import logging
from datetime import timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select, distinct

from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.services.summary_service import generate_weekly_summary, get_week_bounds

logger = logging.getLogger(__name__)

# Single global scheduler instance
scheduler = AsyncIOScheduler(timezone="UTC")


# ─── Job Function ─────────────────────────────────────────────────────────────

async def run_weekly_summaries() -> None:
    """
    Weekly job: generate summaries for all active users.
    Runs every Sunday at 23:59 UTC.

    - Opens its own DB session (not tied to a request)
    - Per-user errors are swallowed so one bad user never blocks others
    - Uses last week's bounds (offset=1) since it runs at end-of-Sunday
    """
    logger.info("APScheduler: weekly summary job started")

    week_start, week_end = get_week_bounds(offset=0)  # current week that just ended

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(distinct(User.id)).where(User.is_active == True)
            )
            user_ids = [row[0] for row in result.all()]
        except Exception as e:
            logger.error(f"Weekly job: failed to fetch user IDs: {e}")
            return

    logger.info(f"Weekly job: processing {len(user_ids)} users for week {week_start} → {week_end}")

    success_count = 0
    skip_count = 0
    error_count = 0

    for user_id in user_ids:
        async with AsyncSessionLocal() as db:
            try:
                result = await generate_weekly_summary(
                    user_id=user_id,
                    week_start=week_start,
                    week_end=week_end,
                    db=db,
                )
                if result is None:
                    skip_count += 1
                else:
                    success_count += 1
            except Exception as e:
                error_count += 1
                logger.error(f"Weekly job: failed for user {user_id}: {e}")

    logger.info(
        f"APScheduler: weekly summary job complete — "
        f"{success_count} generated, {skip_count} skipped, {error_count} errors"
    )


# ─── Lifecycle Helpers ────────────────────────────────────────────────────────

def start_scheduler() -> None:
    """
    Register the weekly job and start the scheduler.
    Called from FastAPI's lifespan startup event.
    """
    scheduler.add_job(
        run_weekly_summaries,
        trigger=CronTrigger(
            day_of_week="sun",
            hour=23,
            minute=59,
            second=0,
            timezone="UTC",
        ),
        id="weekly_summaries",
        name="Weekly fitness summary for all users",
        replace_existing=True,
        misfire_grace_time=3600,   # allow up to 1 hour late if server was down
    )
    scheduler.start()
    logger.info("APScheduler started. Weekly summary job registered (Sunday 23:59 UTC).")


def stop_scheduler() -> None:
    """
    Gracefully shut down the scheduler.
    Called from FastAPI's lifespan shutdown event.
    """
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped.")
