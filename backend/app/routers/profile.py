# backend/app/routers/profile.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User, Profile
from app.models.memory import MemoryFact, FactCategoryEnum
from app.schemas.user import ProfileUpdate, ProfileWithUserOut, OnboardingSubmit
from app.services.memory_service import store_facts
from app.schemas.memory import ExtractedFact

router = APIRouter(prefix="/profile", tags=["profile"])


# ─── Helper: get or create profile ───────────────────────────────────────────
async def _get_or_create_profile(user: User, db: AsyncSession) -> Profile:
    """
    Profiles are created lazily — a user may exist without one
    if they registered before profile creation was added.
    """
    result = await db.execute(
        select(Profile).where(Profile.user_id == user.id)
    )
    profile = result.scalar_one_or_none()

    if profile is None:
        profile = Profile(user_id=user.id)
        db.add(profile)
        await db.commit()
        await db.refresh(profile)

    return profile


def _build_response(user: User, profile: Profile) -> ProfileWithUserOut:
    return ProfileWithUserOut(
        id=profile.id,
        user_id=user.id,
        email=user.email,
        full_name=profile.full_name,
        age=profile.age,
        gender=profile.gender,
        height_cm=profile.height_cm,
        weight_kg=profile.weight_kg,
        fitness_goal=profile.fitness_goal,
        activity_level=profile.activity_level,
        experience_level=profile.experience_level,
        injuries=profile.injuries,
        preferences=profile.preferences,
        onboarding_complete=profile.onboarding_complete,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=profile.updated_at,
    )


# ─── GET /profile/me ──────────────────────────────────────────────────────────
@router.get("/me", response_model=ProfileWithUserOut)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await _get_or_create_profile(current_user, db)
    return _build_response(current_user, profile)


# ─── PUT /profile/me ──────────────────────────────────────────────────────────
@router.put("/me", response_model=ProfileWithUserOut)
async def update_profile(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Reject empty payloads
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No fields provided for update.",
        )

    profile = await _get_or_create_profile(current_user, db)

    for field, value in updates.items():
        setattr(profile, field, value)

    await db.commit()
    await db.refresh(profile)

    return _build_response(current_user, profile)


# ─── POST /profile/onboarding ─────────────────────────────────────────────────
@router.post("/onboarding", response_model=ProfileWithUserOut)
async def submit_onboarding(
    payload: OnboardingSubmit,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Complete the onboarding wizard.

    1. Fills profile fields (name, age, gender, height, weight, goal, activity,
       experience, injuries, preferences).
    2. Sets onboarding_complete = True.
    3. Seeds MemoryFact entries into Postgres + ChromaDB so the AI is
       immediately personalized from the very first chat message.
    """
    profile = await _get_or_create_profile(current_user, db)

    if profile.onboarding_complete:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Onboarding already completed.",
        )

    # ── 1. Write all profile fields ──────────────────────────────────────────
    profile.full_name = payload.full_name
    profile.age = payload.age
    profile.gender = payload.gender
    profile.height_cm = payload.height_cm
    profile.weight_kg = payload.weight_kg
    profile.fitness_goal = payload.fitness_goal
    profile.activity_level = payload.activity_level
    profile.experience_level = payload.experience_level
    profile.injuries = payload.injuries
    profile.preferences = payload.preferences
    profile.onboarding_complete = True

    await db.commit()
    await db.refresh(profile)

    # ── 2. Seed memory facts ─────────────────────────────────────────────────
    # Build ExtractedFact list from the onboarding answers.
    # These land in MemoryFact + ChromaDB so every future chat call
    # can retrieve them via semantic search.
    seed_facts: list[ExtractedFact] = []

    seed_facts.append(ExtractedFact(
        fact=f"User's primary fitness goal is: {payload.fitness_goal}",
        category=FactCategoryEnum.goal,
        confidence=95,
    ))

    activity_label = payload.activity_level.value.replace("_", " ")
    seed_facts.append(ExtractedFact(
        fact=(
            f"User is {payload.experience_level} level with a "
            f"{activity_label} activity level."
        ),
        category=FactCategoryEnum.preference,
        confidence=95,
    ))

    if payload.injuries and payload.injuries.strip():
        seed_facts.append(ExtractedFact(
            fact=f"User reported the following injuries or physical limitations: {payload.injuries.strip()}",
            category=FactCategoryEnum.limitation,
            confidence=95,
        ))

    if payload.preferences and payload.preferences.strip():
        seed_facts.append(ExtractedFact(
            fact=f"User's workout preferences: {payload.preferences.strip()}",
            category=FactCategoryEnum.preference,
            confidence=90,
        ))

    # Store facts (Postgres + ChromaDB) — failure must not break onboarding
    try:
        await store_facts(
            user_id=str(current_user.id),
            facts=seed_facts,
            db=db,
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(
            f"Onboarding memory seeding failed for user {current_user.id}: {e}"
        )

    return _build_response(current_user, profile)