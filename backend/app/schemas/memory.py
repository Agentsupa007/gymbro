from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional
from app.models.memory import FactCategoryEnum


# ─── Extractor Internal Schemas ───────────────────────────────────────────────
# Used to parse the raw JSON that Gemini returns from the extractor call

class ExtractedFact(BaseModel):
    """A single fact as returned by the Gemini extractor."""
    category: FactCategoryEnum
    fact: str
    confidence: int = Field(ge=0, le=100)


class ExtractorResponse(BaseModel):
    """The full JSON response from the extractor prompt."""
    facts: list[ExtractedFact] = []


# ─── API Response Schemas ─────────────────────────────────────────────────────
# Used by GET /memory/facts

class MemoryFactOut(BaseModel):
    """A stored memory fact returned to the client."""
    id: str
    category: FactCategoryEnum
    fact: str
    confidence: int
    is_active: bool
    source_message_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MemoryFactsResponse(BaseModel):
    """Paginated list of memory facts."""
    facts: list[MemoryFactOut]
    total: int


# ─── Weekly Summary Schemas ───────────────────────────────────────────────────
# Used by POST /memory/summarize

class WeeklySummaryData(BaseModel):
    """The structured JSON returned by the Gemini summary pipeline."""
    narrative: str
    highlights: list[str] = []
    concerns: list[str] = []
    trends: list[str] = []
    focus_next_week: list[str] = []
    activity_score: int = Field(ge=0, le=100)


class WeeklySummaryOut(BaseModel):
    """Response shape for POST /memory/summarize."""
    week_start: date
    week_end: date
    summary: WeeklySummaryData