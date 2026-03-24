from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.memory import MemoryFact, FactCategoryEnum
from app.schemas.memory import MemoryFactOut, MemoryFactsResponse, WeeklySummaryOut
from app.services.summary_service import generate_weekly_summary, get_week_bounds

router = APIRouter(prefix="/memory", tags=["memory"])


# ─── GET /memory/facts ────────────────────────────────────────────────────────

@router.get("/facts", response_model=MemoryFactsResponse)
async def get_memory_facts(
    category: FactCategoryEnum | None = Query(
        default=None,
        description="Filter by category (goal, preference, limitation, etc.)"
    ),
    active_only: bool = Query(
        default=True,
        description="Return only active facts (not soft-deleted)"
    ),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return stored memory facts for the current user.

    - Filter by category using the `category` query param
    - `active_only=true` (default) hides soft-deleted facts
    - Supports pagination via `limit` and `offset`
    """
    query = select(MemoryFact).where(MemoryFact.user_id == current_user.id)

    if active_only:
        query = query.where(MemoryFact.is_active == True)

    if category:
        query = query.where(MemoryFact.category == category)

    # Total count for pagination
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar_one()

    # Paginated results — newest first
    query = query.order_by(MemoryFact.updated_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    facts = result.scalars().all()

    return MemoryFactsResponse(
        facts=[MemoryFactOut.model_validate(f) for f in facts],
        total=total,
    )


# ─── DELETE /memory/facts/{fact_id} ──────────────────────────────────────────

@router.delete("/facts/{fact_id}", status_code=204)
async def delete_memory_fact(
    fact_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Soft-delete a memory fact (sets is_active=False).
    Users can remove facts they don't want the AI to remember.
    """
    result = await db.execute(
        select(MemoryFact).where(
            MemoryFact.id == fact_id,
            MemoryFact.user_id == current_user.id,
        )
    )
    fact = result.scalar_one_or_none()

    if not fact:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fact not found",
        )

    fact.is_active = False
    await db.commit()


# ─── POST /memory/summarize ───────────────────────────────────────────────────

@router.post("/summarize", response_model=WeeklySummaryOut)
async def trigger_weekly_summary(
    week_offset: int = Query(
        default=0,
        ge=0,
        le=52,
        description="0 = current week, 1 = last week, 2 = two weeks ago, etc."
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Manually trigger the weekly summary pipeline for the current user.

    Useful for testing without waiting for the Sunday 23:59 cron job.

    - week_offset=0  → summarise the current (ongoing) week
    - week_offset=1  → summarise last week (recommended for a complete data set)

    Returns the structured summary JSON on success, or a detail message
    if there was insufficient activity to generate a summary.
    """
    week_start, week_end = get_week_bounds(offset=week_offset)

    result = await generate_weekly_summary(
        user_id=str(current_user.id),
        week_start=week_start,
        week_end=week_end,
        db=db,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_200_OK,
            detail=(
                f"Insufficient activity for week {week_start} → {week_end}. "
                "Summary skipped. Chat with GymBro or log some metrics first."
            ),
        )

    return {
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "summary": result,
    }