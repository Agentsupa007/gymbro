"""
utils.py — Shared helpers for extraction and retrieval evaluation.
"""

import json
from pathlib import Path


PERSONAS_DIR = Path(__file__).parent / "personas"


def load_all_personas() -> list[dict]:
    personas = []
    for path in sorted(PERSONAS_DIR.glob("user_*.json")):
        with open(path) as f:
            personas.append(json.load(f))
    return personas


def load_persona(filename: str) -> dict:
    with open(PERSONAS_DIR / filename) as f:
        return json.load(f)


# ─── Fact Matching ────────────────────────────────────────────────────────────
# Uses category match + word-overlap ≥ threshold.
# Mirrors the dedup logic already in memory_service.py (_content_words / 0.6 overlap).

_STOPWORDS = {
    "user", "the", "a", "an", "is", "are", "was", "were", "be", "been",
    "has", "have", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "to", "of", "in", "on", "at", "for", "and",
    "or", "but", "not", "with", "their", "they", "that", "this", "it",
    "wants", "prefers", "likes", "dislikes", "enjoys", "avoids",
}


def _content_words(text: str) -> set[str]:
    return {w for w in text.lower().split() if w not in _STOPWORDS and len(w) > 2}


def facts_match(extracted_fact: str, extracted_category: str,
                gt_fact: str, gt_category: str,
                overlap_threshold: float = 0.45) -> bool:
    """
    Returns True if an extracted fact matches a ground-truth fact.

    Rules:
    - Category must match exactly.
    - Word overlap (Jaccard-style on content words) must exceed threshold.

    threshold=0.45 is intentionally lower than the dedup threshold (0.6)
    because extracted facts are paraphrases of GT, not near-duplicates.
    """
    if extracted_category != gt_category:
        return False

    extracted_words = _content_words(extracted_fact)
    gt_words = _content_words(gt_fact)

    if not extracted_words or not gt_words:
        return False

    intersection = len(extracted_words & gt_words)
    smaller = min(len(extracted_words), len(gt_words))
    overlap = intersection / smaller

    return overlap >= overlap_threshold


def match_extracted_to_gt(
    extracted_facts: list[dict],
    ground_truth_facts: list[dict],
    overlap_threshold: float = 0.45,
) -> tuple[list[tuple], set[str], set[str]]:
    """
    Match extracted facts to ground truth facts.

    Returns:
        matched_pairs   — list of (extracted_fact_dict, gt_fact_dict) matched pairs
        matched_gt_ids  — set of gt fact IDs that were matched
        matched_ext_idx — set of extracted fact indices that were matched
    """
    matched_pairs = []
    matched_gt_ids = set()
    matched_ext_idx = set()

    for ext_idx, ext in enumerate(extracted_facts):
        for gt in ground_truth_facts:
            if gt["id"] in matched_gt_ids:
                continue  # already matched
            if facts_match(
                ext["fact"], ext["category"],
                gt["fact"], gt["category"],
                overlap_threshold,
            ):
                matched_pairs.append((ext, gt))
                matched_gt_ids.add(gt["id"])
                matched_ext_idx.add(ext_idx)
                break  # one extracted fact matches at most one GT fact

    return matched_pairs, matched_gt_ids, matched_ext_idx


# ─── Metric Computation ───────────────────────────────────────────────────────

def compute_extraction_metrics(
    extracted_facts: list[dict],
    ground_truth_facts: list[dict],
    overlap_threshold: float = 0.45,
) -> dict:
    """
    Compute Precision, Recall, F1, and Category Accuracy for a single user.
    """
    if not extracted_facts and not ground_truth_facts:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0, "category_accuracy": 1.0, "matched": 0, "extracted": 0, "gt_total": 0}

    matched_pairs, matched_gt_ids, matched_ext_idx = match_extracted_to_gt(
        extracted_facts, ground_truth_facts, overlap_threshold
    )

    n_matched = len(matched_pairs)
    n_extracted = len(extracted_facts)
    n_gt = len(ground_truth_facts)

    precision = n_matched / n_extracted if n_extracted > 0 else 0.0
    recall = n_matched / n_gt if n_gt > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    # Category accuracy: among matched pairs, how many had the right category?
    # (Since category must match for a pair to form, this is always 1.0 with current matcher.
    #  Kept here for future looser matchers that allow cross-category matching.)
    correct_category = sum(
        1 for ext, gt in matched_pairs if ext["category"] == gt["category"]
    )
    category_accuracy = correct_category / n_matched if n_matched > 0 else 0.0

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "category_accuracy": round(category_accuracy, 4),
        "matched": n_matched,
        "extracted": n_extracted,
        "gt_total": n_gt,
    }


def compute_retrieval_metrics(
    retrieved_fact_texts: list[str],
    relevant_gt_facts: list[dict],
    top_k: int = 5,
) -> dict:
    """
    Compute P@k, R@k, and MRR for a single probe query.

    Args:
        retrieved_fact_texts : ordered list of fact_text strings from ChromaDB (top-k, rank 0 = best)
        relevant_gt_facts    : list of GT fact dicts whose facts are relevant to this query
        top_k                : k for P@k and R@k
    """
    relevant_texts = {_normalize(gt["fact"]) for gt in relevant_gt_facts}

    hits = []
    covered_gt_indices = set()
    for rank, retrieved in enumerate(retrieved_fact_texts[:top_k], start=1):
        is_hit = False
        ret_words = _content_words(retrieved)
        if ret_words:
            for gt_idx, gt in enumerate(relevant_gt_facts):
                gt_words = set(_normalize(gt["fact"]).split())
                if gt_words:
                    overlap = len(ret_words & gt_words) / min(len(ret_words), len(gt_words))
                    if overlap >= 0.45:
                        covered_gt_indices.add(gt_idx)
                        is_hit = True
        hits.append(is_hit)

    n_hits = sum(hits)
    precision_at_k = n_hits / top_k if top_k > 0 else 0.0
    recall_at_k = len(covered_gt_indices) / len(relevant_gt_facts) if relevant_gt_facts else 0.0

    # MRR: reciprocal rank of first relevant result
    mrr = 0.0
    for rank, is_hit in enumerate(hits, start=1):
        if is_hit:
            mrr = 1.0 / rank
            break

    return {
        "precision_at_k": round(precision_at_k, 4),
        "recall_at_k": round(recall_at_k, 4),
        "mrr": round(mrr, 4),
        "hits": hits,
        "n_hits": n_hits,
    }


def _normalize(text: str) -> str:
    return " ".join(_content_words(text))


def _is_relevant(retrieved_text: str, relevant_normalized: set[str]) -> bool:
    """
    Check if a retrieved fact text is semantically relevant to any ground-truth fact.
    Uses the same word-overlap approach as fact matching.
    """
    ret_words = _content_words(retrieved_text)
    if not ret_words:
        return False

    for rel_norm in relevant_normalized:
        rel_words = set(rel_norm.split())
        if not rel_words:
            continue
        overlap = len(ret_words & rel_words) / min(len(ret_words), len(rel_words))
        if overlap >= 0.45:
            return True
    return False


def print_table(rows: list[dict], title: str = "") -> None:
    """Pretty-print a list of dicts as a table."""
    if not rows:
        print(f"{title}: (no data)")
        return
    if title:
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}")
    keys = list(rows[0].keys())
    col_widths = {k: max(len(k), max(len(str(r.get(k, ""))) for r in rows)) for k in keys}
    header = "  ".join(k.ljust(col_widths[k]) for k in keys)
    print(header)
    print("-" * len(header))
    for row in rows:
        print("  ".join(str(row.get(k, "")).ljust(col_widths[k]) for k in keys))
