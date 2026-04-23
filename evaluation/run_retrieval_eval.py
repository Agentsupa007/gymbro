"""
run_retrieval_eval.py

Retrieval Quality Evaluation — Part 3 of the GymBro evaluation pipeline.

For each synthetic user:
  1. Seed ChromaDB by running all user messages through the full memory pipeline
     (process_message_for_memory → extract → store Postgres + ChromaDB)
  2. For each probe query, retrieve top-5 memories from ChromaDB
  3. Compare retrieved facts against query_relevance_map
  4. Compute P@5, R@5, MRR per query and macro-average across all users

Also runs a Recency Bias Test:
  - Injects an old duplicate fact (timestamp = 180 days ago)
  - Injects a newer equivalent fact (timestamp = today)
  - Confirms the newer one ranks higher in retrieval

Run from the backend directory:
  cd backend
  python ../evaluation/run_retrieval_eval.py

IMPORTANT: Uses isolated eval_ user IDs and eval_episodes / eval_summaries
ChromaDB collections — production data is never touched.
"""

import asyncio
import json
import sys
import time
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── Make backend app importable ───────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, delete

from app.core.config import settings
from app.models.user import User
from app.models.memory import MemoryFact
from app.services.memory_service import process_message_for_memory, get_relevant_memories
from app.services.embedding_service import store_memory_embedding, _get_chroma_collections

# ── Eval utils ────────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))
from utils import load_all_personas, compute_retrieval_metrics, print_table

logging.basicConfig(level=logging.WARNING)  # suppress info logs during eval

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

# ── Isolated ChromaDB collections for eval ────────────────────────────────────
# We patch _get_chroma_collections at runtime to return eval-specific collections.
# This guarantees zero pollution of the production episodes/summaries collections.

import chromadb
from chromadb.config import Settings as ChromaSettings

_eval_chroma_client = None
_eval_episodes_col = None
_eval_summaries_col = None


def _get_eval_chroma_collections():
    global _eval_chroma_client, _eval_episodes_col, _eval_summaries_col

    if _eval_episodes_col is not None:
        return _eval_episodes_col, _eval_summaries_col

    _eval_chroma_client = chromadb.HttpClient(
        host=settings.CHROMA_HOST,
        port=settings.CHROMA_PORT,
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    _eval_episodes_col = _eval_chroma_client.get_or_create_collection(
        name="eval_episodes",
        metadata={"hnsw:space": "cosine"},
    )
    _eval_summaries_col = _eval_chroma_client.get_or_create_collection(
        name="eval_summaries",
        metadata={"hnsw:space": "cosine"},
    )
    return _eval_episodes_col, _eval_summaries_col


def _patch_embedding_service():
    """Redirect all ChromaDB calls in embedding_service to eval collections."""
    import app.services.embedding_service as emb
    emb._get_chroma_collections = _get_eval_chroma_collections


def _clear_eval_user_data(user_id: str):
    """Remove all previously stored eval data for this user from ChromaDB."""
    episodes, _ = _get_eval_chroma_collections()
    try:
        existing = episodes.get(where={"user_id": user_id}, include=[])
        if existing["ids"]:
            episodes.delete(ids=existing["ids"])
            print(f"  Cleared {len(existing['ids'])} existing entries for {user_id}")
    except Exception:
        pass


# ── DB session factory (async) ─────────────────────────────────────────────────

def _make_session_factory():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    return sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# ── Eval user lifecycle ───────────────────────────────────────────────────────

async def create_eval_users(personas: list[dict], session_factory) -> None:
    """
    Insert synthetic users into the users table so FK constraints are satisfied.
    Uses a dummy hashed_password — these users cannot log in.
    Skips users that already exist.
    """
    async with session_factory() as db:
        for persona in personas:
            user_id = persona["user_id"]
            existing = await db.execute(select(User).where(User.id == user_id))
            if existing.scalar_one_or_none():
                continue
            user = User(
                id=user_id,
                email=f"{user_id}@eval.gymbro.internal",
                hashed_password="$eval$not_a_real_hash",
                is_active=True,
                is_verified=False,
            )
            db.add(user)
        await db.commit()
    print(f"  Eval users ensured in users table ({len(personas)} users)")


async def delete_eval_users(personas: list[dict], session_factory) -> None:
    """
    Remove all eval users and their data from Postgres after the eval.
    Must delete child rows (memory_facts) before parent (users) since
    bulk DELETE statements don't trigger ORM-level cascade.
    """
    async with session_factory() as db:
        user_ids = [p["user_id"] for p in personas]
        await db.execute(delete(MemoryFact).where(MemoryFact.user_id.in_(user_ids)))
        await db.execute(delete(User).where(User.id.in_(user_ids)))
        await db.commit()
    print(f"  Cleaned up {len(personas)} eval users from Postgres")


# ── Seeding ───────────────────────────────────────────────────────────────────

async def seed_user(persona: dict, session_factory) -> int:
    """
    Feed all user messages through the full memory pipeline for a persona.
    Returns the number of facts stored.
    """
    user_id = persona["user_id"]
    messages = persona["conversation_messages"]

    _clear_eval_user_data(user_id)

    stored_total = 0
    async with session_factory() as db:
        for msg in messages:
            await process_message_for_memory(
                user_id=user_id,
                user_message=msg,
                db=db,
            )

    # Count what ended up in ChromaDB
    episodes, _ = _get_eval_chroma_collections()
    result = episodes.get(where={"user_id": user_id}, include=[])
    stored_total = len(result["ids"])
    return stored_total


# ── Retrieval evaluation ──────────────────────────────────────────────────────

async def evaluate_retrieval_for_user(persona: dict) -> dict:
    """
    For each probe query, retrieve top-5 memories and compute P@5, R@5, MRR.
    """
    user_id = persona["user_id"]
    name = persona["profile"]["full_name"]
    ground_truth = {gt["id"]: gt for gt in persona["ground_truth_facts"]}
    probe_queries = persona["probe_queries"]

    print(f"\n[{name}] Evaluating {len(probe_queries)} probe queries...")

    query_results = []
    for pq in probe_queries:
        query = pq["query"]
        relevant_ids = pq["relevant_fact_ids"]
        relevant_gts = [ground_truth[gid] for gid in relevant_ids if gid in ground_truth]

        retrieved = await get_relevant_memories(user_id=user_id, query=query, top_k=5)
        retrieved_texts = [r["fact_text"] for r in retrieved]

        metrics = compute_retrieval_metrics(retrieved_texts, relevant_gts, top_k=5)

        print(f"  Q: \"{query[:60]}\"")
        print(f"     P@5={metrics['precision_at_k']:.2f}  R@5={metrics['recall_at_k']:.2f}  MRR={metrics['mrr']:.2f}  hits={metrics['n_hits']}/{len(relevant_gts)}")

        query_results.append({
            "query": query,
            "relevant_fact_ids": relevant_ids,
            "retrieved_texts": retrieved_texts,
            **metrics,
        })

    # Macro averages for this user
    n_q = len(query_results)
    avg_p = sum(q["precision_at_k"] for q in query_results) / n_q
    avg_r = sum(q["recall_at_k"] for q in query_results) / n_q
    avg_mrr = sum(q["mrr"] for q in query_results) / n_q

    return {
        "user_id": user_id,
        "name": name,
        "n_queries": n_q,
        "avg_precision_at_5": round(avg_p, 4),
        "avg_recall_at_5": round(avg_r, 4),
        "avg_mrr": round(avg_mrr, 4),
        "queries": query_results,
    }


# ── Recency Bias Test ─────────────────────────────────────────────────────────

async def run_recency_bias_test():
    """
    Inject two semantically identical facts for a test user:
      - One with created_at = 180 days ago  (old)
      - One with created_at = today          (new)
    Then retrieve and assert the new fact ranks above the old one.
    """
    print("\n" + "="*60)
    print("  Recency Bias Test")
    print("="*60)

    test_user_id = "eval_recency_test"
    fact_text_old = "User has chronic lower back pain from a disc bulge"
    fact_text_new = "User has chronic lower back pain from a disc bulge"  # identical text
    query = "My back has been hurting a lot lately"

    episodes, _ = _get_eval_chroma_collections()

    # Clear any previous test data
    try:
        existing = episodes.get(where={"user_id": test_user_id}, include=[])
        if existing["ids"]:
            episodes.delete(ids=existing["ids"])
    except Exception:
        pass

    now = datetime.now(timezone.utc)
    old_ts = (now - timedelta(days=180)).timestamp()
    new_ts = now.timestamp()

    old_dt = datetime.fromtimestamp(old_ts, tz=timezone.utc)
    new_dt = datetime.fromtimestamp(new_ts, tz=timezone.utc)

    await store_memory_embedding(
        fact_id="recency_test_old",
        user_id=test_user_id,
        fact_text=fact_text_old,
        category="limitation",
        confidence=90,
        created_at=old_dt,
    )

    # Cosine dedup would normally block the second identical fact (similarity=1.0 > 0.92).
    # We bypass by storing directly with a different ID and distinct timestamp.
    # This simulates the case where a user re-states a fact months later.
    from app.services.embedding_service import embed_text
    vector = await embed_text(fact_text_new)
    episodes.upsert(
        ids=["recency_test_new"],
        embeddings=[vector],
        metadatas=[{
            "user_id": test_user_id,
            "category": "limitation",
            "confidence": 90,
            "timestamp": new_ts,
            "fact_text": fact_text_new,
        }],
        documents=[fact_text_new],
    )

    # Retrieve and check ordering
    retrieved = await get_relevant_memories(user_id=test_user_id, query=query, top_k=2)

    passed = False
    if len(retrieved) == 2:
        # New fact should have higher combined_score
        ids_ordered = [r.get("fact_id", "") for r in retrieved]
        scores_ordered = [(r.get("fact_id", ""), r.get("combined_score", 0), r.get("recency_score", 0)) for r in retrieved]
        print(f"  Retrieved order: {scores_ordered}")
        if ids_ordered[0] == "recency_test_new":
            passed = True
            print("  PASS — newer fact ranked above older fact")
        else:
            print("  FAIL — older fact ranked above newer fact (recency weighting not working)")
    elif len(retrieved) == 1:
        print(f"  WARN — only 1 result returned (dedup may have collapsed them): {retrieved}")
        passed = None
    else:
        print(f"  FAIL — expected 2 results, got {len(retrieved)}")

    # Cleanup
    try:
        episodes.delete(ids=["recency_test_old", "recency_test_new"])
    except Exception:
        pass

    return {"passed": passed, "retrieved": retrieved}


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    _patch_embedding_service()

    personas = load_all_personas()
    print(f"Loaded {len(personas)} personas.")

    session_factory = _make_session_factory()

    # ── Phase 0: Create eval users in Postgres ────────────────────────────────
    print("\n" + "="*60)
    print("  Phase 0: Creating eval users in Postgres")
    print("="*60)
    await create_eval_users(personas, session_factory)

    # ── Phase 1: Seed ChromaDB ────────────────────────────────────────────────
    print("\n" + "="*60)
    print("  Phase 1: Seeding ChromaDB via full memory pipeline")
    print("="*60)
    for persona in personas:
        name = persona["profile"]["full_name"]
        n = await seed_user(persona, session_factory)
        print(f"  {name} ({persona['user_id']}): {n} facts stored in eval_episodes")

    # ── Phase 2: Retrieval evaluation ─────────────────────────────────────────
    print("\n" + "="*60)
    print("  Phase 2: Retrieval Evaluation")
    print("="*60)
    all_results = []
    for persona in personas:
        result = await evaluate_retrieval_for_user(persona)
        all_results.append(result)

    # ── Summary table ─────────────────────────────────────────────────────────
    table_rows = [
        {
            "User": r["name"],
            "Queries": r["n_queries"],
            "P@5": f"{r['avg_precision_at_5']:.2f}",
            "R@5": f"{r['avg_recall_at_5']:.2f}",
            "MRR": f"{r['avg_mrr']:.2f}",
        }
        for r in all_results
    ]
    print_table(table_rows, title="Retrieval Quality — Per User")

    n = len(all_results)
    macro_p = sum(r["avg_precision_at_5"] for r in all_results) / n
    macro_r = sum(r["avg_recall_at_5"] for r in all_results) / n
    macro_mrr = sum(r["avg_mrr"] for r in all_results) / n

    print(f"\nMacro Averages across {n} users:")
    print(f"  P@5  : {macro_p:.4f}")
    print(f"  R@5  : {macro_r:.4f}")
    print(f"  MRR  : {macro_mrr:.4f}")

    # ── Phase 3: Recency Bias Test ────────────────────────────────────────────
    recency_result = await run_recency_bias_test()

    # ── Save results ──────────────────────────────────────────────────────────
    output = {
        "summary": {
            "macro_precision_at_5": round(macro_p, 4),
            "macro_recall_at_5": round(macro_r, 4),
            "macro_mrr": round(macro_mrr, 4),
        },
        "per_user": all_results,
        "recency_bias_test": recency_result,
    }
    out_path = RESULTS_DIR / "retrieval_results.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\nFull results saved to {out_path}")

    # ── Cleanup: Remove eval users from Postgres ──────────────────────────────
    print("\n" + "="*60)
    print("  Cleanup: Removing eval users from Postgres")
    print("="*60)
    await delete_eval_users(personas, session_factory)


if __name__ == "__main__":
    asyncio.run(main())
