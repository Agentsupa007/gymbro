"""
run_extraction_eval.py

Extraction Quality Evaluation — Part 2 of the GymBro evaluation pipeline.

For each synthetic user:
  1. Feed all user-turn messages through the existing extract_facts_from_message()
  2. Collect all extracted facts across the full conversation
  3. Compare against ground-truth facts using category + word-overlap matching
  4. Compute Precision, Recall, F1, Category Accuracy

Run from the backend directory so the app imports resolve:
  cd backend
  python ../evaluation/run_extraction_eval.py
"""

import asyncio
import json
import sys
import os
from pathlib import Path
from collections import defaultdict

# ── Make backend app importable ───────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.services.memory_service import extract_facts_from_message

# ── Eval utils ────────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))
from utils import (
    load_all_personas,
    compute_extraction_metrics,
    match_extracted_to_gt,
    print_table,
)

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)


async def run_extraction_for_user(persona: dict) -> dict:
    """
    Run the extractor over all user messages for a single persona.
    Returns a result dict with per-user metrics and the raw extracted facts.
    """
    user_id = persona["user_id"]
    name = persona["profile"]["full_name"]
    messages = persona["conversation_messages"]
    ground_truth = persona["ground_truth_facts"]

    print(f"\n[{name}] Processing {len(messages)} messages...")

    all_extracted = []
    for i, msg in enumerate(messages, start=1):
        facts = await extract_facts_from_message(msg)
        extracted_dicts = [{"category": f.category.value, "fact": f.fact, "confidence": f.confidence} for f in facts]
        if extracted_dicts:
            print(f"  msg {i:02d}: {len(extracted_dicts)} fact(s) extracted")
            for f in extracted_dicts:
                print(f"           [{f['category']}] {f['fact']} (conf={f['confidence']})")
        all_extracted.extend(extracted_dicts)

    # Deduplicate extracted facts by category+fact text (mirrors production dedup)
    seen = set()
    deduped_extracted = []
    for f in all_extracted:
        key = (f["category"], f["fact"].lower().strip())
        if key not in seen:
            seen.add(key)
            deduped_extracted.append(f)

    print(f"  Total extracted (after dedup): {len(deduped_extracted)}")

    metrics = compute_extraction_metrics(deduped_extracted, ground_truth)

    # Show which GT facts were matched and which were missed
    matched_pairs, matched_gt_ids, _ = match_extracted_to_gt(deduped_extracted, ground_truth)
    missed_gt = [gt for gt in ground_truth if gt["id"] not in matched_gt_ids]
    extra_extracted = [
        f for i, f in enumerate(deduped_extracted)
        if i not in {idx for idx, _ in enumerate(deduped_extracted) if any(
            ext["fact"] == f["fact"] for ext, _ in matched_pairs
        )}
    ]

    print(f"  Metrics → P={metrics['precision']:.2f}  R={metrics['recall']:.2f}  F1={metrics['f1']:.2f}  CatAcc={metrics['category_accuracy']:.2f}")
    if missed_gt:
        print(f"  Missed GT facts ({len(missed_gt)}):")
        for gt in missed_gt:
            print(f"    [MISS] [{gt['category']}] {gt['fact']}")

    return {
        "user_id": user_id,
        "name": name,
        "ground_truth_count": len(ground_truth),
        "extracted_count": len(deduped_extracted),
        "matched": metrics["matched"],
        "precision": metrics["precision"],
        "recall": metrics["recall"],
        "f1": metrics["f1"],
        "category_accuracy": metrics["category_accuracy"],
        "extracted_facts": deduped_extracted,
        "missed_gt_facts": missed_gt,
    }


async def main():
    personas = load_all_personas()
    print(f"Loaded {len(personas)} personas.")
    print("Running extraction evaluation...\n")

    all_results = []
    for persona in personas:
        result = await run_extraction_for_user(persona)
        all_results.append(result)

    # ── Per-user summary table ────────────────────────────────────────────────
    table_rows = [
        {
            "User": r["name"],
            "GT Facts": r["ground_truth_count"],
            "Extracted": r["extracted_count"],
            "Matched": r["matched"],
            "Precision": f"{r['precision']:.2f}",
            "Recall": f"{r['recall']:.2f}",
            "F1": f"{r['f1']:.2f}",
            "CatAcc": f"{r['category_accuracy']:.2f}",
        }
        for r in all_results
    ]
    print_table(table_rows, title="Extraction Quality — Per User")

    # ── Macro averages ────────────────────────────────────────────────────────
    n = len(all_results)
    avg_precision = sum(r["precision"] for r in all_results) / n
    avg_recall = sum(r["recall"] for r in all_results) / n
    avg_f1 = sum(r["f1"] for r in all_results) / n
    avg_cat_acc = sum(r["category_accuracy"] for r in all_results) / n

    print(f"\nMacro Averages across {n} users:")
    print(f"  Precision : {avg_precision:.4f}")
    print(f"  Recall    : {avg_recall:.4f}")
    print(f"  F1        : {avg_f1:.4f}")
    print(f"  CatAcc    : {avg_cat_acc:.4f}")

    # ── Category-level breakdown ──────────────────────────────────────────────
    category_stats = defaultdict(lambda: {"gt": 0, "matched": 0})
    for r in all_results:
        persona = next(p for p in personas if p["user_id"] == r["user_id"])
        for gt in persona["ground_truth_facts"]:
            category_stats[gt["category"]]["gt"] += 1
        for ext, gt in match_extracted_to_gt(r["extracted_facts"], persona["ground_truth_facts"])[0]:
            category_stats[gt["category"]]["matched"] += 1

    cat_rows = [
        {
            "Category": cat,
            "GT Count": stats["gt"],
            "Matched": stats["matched"],
            "Recall": f"{stats['matched']/stats['gt']:.2f}" if stats["gt"] > 0 else "N/A",
        }
        for cat, stats in sorted(category_stats.items())
    ]
    print_table(cat_rows, title="Recall by Memory Category")

    # ── Save full results to JSON ─────────────────────────────────────────────
    output = {
        "summary": {
            "avg_precision": round(avg_precision, 4),
            "avg_recall": round(avg_recall, 4),
            "avg_f1": round(avg_f1, 4),
            "avg_category_accuracy": round(avg_cat_acc, 4),
        },
        "per_user": all_results,
        "category_breakdown": {
            cat: {
                "gt_count": s["gt"],
                "matched": s["matched"],
                "recall": round(s["matched"] / s["gt"], 4) if s["gt"] > 0 else 0.0,
            }
            for cat, s in category_stats.items()
        },
    }
    out_path = RESULTS_DIR / "extraction_results.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nFull results saved to {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
