#!/usr/bin/env python3
"""
AEGIS — Evaluate classifier accuracy with real customer data.

Loads tickets from CSV/JSON, runs stratified 5-fold cross-validation,
and reports detailed metrics: accuracy, precision, recall, F1-score,
confusion matrix, average confidence, response time, and identifies
problematic categories.

Usage:
    python scripts/evaluate_real_data.py --file tickets_cliente.csv
    python scripts/evaluate_real_data.py --file tickets_cliente.csv --benchmark
    python scripts/evaluate_real_data.py --file tickets_cliente.json --output report.json
    python scripts/evaluate_real_data.py --file tickets_cliente.csv --folds 10
"""

import argparse
import csv
import json
import sys
import time
import random
from pathlib import Path
from collections import Counter

# Add project root to path so we can import classifier modules
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from classifier import (
    client as chroma_client,
    model as embedding_model,
    create_collection,
    load_tickets_to_db,
    classify_ticket,
    classify_by_keywords,
    CONFIDENCE_THRESHOLD,
)

# ── Constants ─────────────────────────────────────────────────
BENCHMARK_ACCURACY = 0.75  # Current benchmark from synthetic data


# ── Loaders (reuse same logic as import_real_data.py) ─────────

def load_from_csv(filepath: Path) -> list[dict]:
    """Load tickets from a CSV file."""
    required_cols = {"id", "description", "resolution", "category"}

    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            print("❌ CSV file is empty or has no header row.")
            sys.exit(1)

        missing = required_cols - set(reader.fieldnames)
        if missing:
            print(f"❌ CSV missing required columns: {', '.join(sorted(missing))}")
            sys.exit(1)

        tickets = []
        for row in reader:
            ticket = {
                "id": str(row["id"]).strip(),
                "description": str(row["description"]).strip(),
                "resolution": str(row["resolution"]).strip(),
                "category": str(row["category"]).strip().upper(),
            }
            if ticket["id"] and ticket["description"]:
                tickets.append(ticket)
    return tickets


def load_from_json(filepath: Path) -> list[dict]:
    """Load tickets from a JSON file."""
    with open(filepath, encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON file: {e}")
            sys.exit(1)

    if not isinstance(data, list):
        print("❌ JSON file must contain an array of ticket objects.")
        sys.exit(1)

    tickets = []
    for item in data:
        ticket = {
            "id": str(item["id"]).strip(),
            "description": str(item["description"]).strip(),
            "resolution": str(item["resolution"]).strip(),
            "category": str(item["category"]).strip().upper(),
        }
        if ticket["id"] and ticket["description"]:
            tickets.append(ticket)
    return tickets


# ── Cross-validation ──────────────────────────────────────────

def stratified_folds(tickets: list[dict], n_folds: int, seed: int = 42):
    """Split tickets into n_folds stratified by category."""
    categories = sorted(set(t["category"] for t in tickets))
    by_cat = {c: [] for c in categories}
    for t in tickets:
        by_cat[t["category"]].append(t)

    rng = random.Random(seed)
    folds = [[] for _ in range(n_folds)]
    for cat, cat_tickets in by_cat.items():
        rng.shuffle(cat_tickets)
        for i, t in enumerate(cat_tickets):
            folds[i % n_folds].append(t)
    return folds, categories


def run_cross_validation(tickets: list[dict], n_folds: int = 5) -> dict:
    """
    Run stratified k-fold cross-validation on the given tickets.
    Returns a dict with all metrics.
    """
    folds, categories = stratified_folds(tickets, n_folds)
    all_categories = categories + ["UNKNOWN"]

    all_actual = []
    all_predicted = []
    all_confidences = []
    all_methods = []
    all_times = []  # response time per ticket

    print(f"\n{'=' * 70}")
    print(f"🛡️  CROSS-VALIDATION — {n_folds}-fold on {len(tickets)} tickets")
    print(f"   Categories ({len(categories)}): {', '.join(categories)}")
    print(f"{'=' * 70}\n")

    for fold_idx in range(n_folds):
        print(f"{'─' * 70}")
        print(f"📁 Fold {fold_idx + 1}/{n_folds}")
        print(f"{'─' * 70}")

        # Split
        test_set = folds[fold_idx]
        train_set = []
        for f in range(n_folds):
            if f != fold_idx:
                train_set.extend(folds[f])

        print(f"   Train: {len(train_set)} tickets | Test: {len(test_set)} tickets")

        # Train
        collection = create_collection(f"eval_fold_{fold_idx}")
        load_tickets_to_db(train_set, collection)

        # Test
        fold_actual = []
        fold_predicted = []
        fold_confidences = []
        fold_methods = []
        fold_times = []

        for ticket in test_set:
            description = ticket["description"]
            actual = ticket["category"]

            # Measure response time
            start = time.perf_counter()
            result = classify_ticket(description, collection)
            elapsed = time.perf_counter() - start

            predicted = result["category"]
            confidence = result["confidence"]
            method_raw = result.get("method", "unknown")

            # Clean method name
            if "vector_fallback_keyword" in method_raw:
                method = "keyword_fallback"
            else:
                method = "vector_weighted"

            # If UNKNOWN or low confidence → considered incorrect for metrics
            if predicted == "UNKNOWN" or confidence < CONFIDENCE_THRESHOLD:
                predicted = "UNKNOWN"

            fold_actual.append(actual)
            fold_predicted.append(predicted)
            fold_confidences.append(confidence)
            fold_methods.append(method)
            fold_times.append(elapsed)

        all_actual.extend(fold_actual)
        all_predicted.extend(fold_predicted)
        all_confidences.extend(fold_confidences)
        all_methods.extend(fold_methods)
        all_times.extend(fold_times)

        # Fold accuracy
        fold_correct = sum(1 for a, p in zip(fold_actual, fold_predicted) if a == p)
        fold_total = len(fold_actual)
        fold_avg_time = sum(fold_times) / len(fold_times) if fold_times else 0
        print(f"   ✅ Fold accuracy: {fold_correct}/{fold_total} = {fold_correct / fold_total:.1%}")
        print(f"   ⏱  Avg response: {fold_avg_time * 1000:.1f} ms")

    # ── Compute metrics ────────────────────────────────────────
    total_tested = len(all_actual)
    correct = sum(1 for a, p in zip(all_actual, all_predicted) if a == p)
    accuracy = correct / total_tested if total_tested > 0 else 0
    avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0
    avg_time = sum(all_times) / len(all_times) if all_times else 0

    # Method distribution
    method_counts = Counter(all_methods)

    # Confusion matrix
    confusion = {a: {p: 0 for p in all_categories} for a in all_categories}
    for a, p in zip(all_actual, all_predicted):
        confusion[a][p] += 1

    # Per-category metrics
    per_category = {}
    problematic = []

    for cat in categories:
        tp = confusion[cat][cat]
        fp = sum(confusion[a][cat] for a in all_categories if a != cat)
        fn = sum(confusion[cat][p] for p in all_categories if p != cat)
        support = sum(confusion[cat][p] for p in all_categories)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        per_category[cat] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "support": support,
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
        }

        # Identify problematic categories
        issues = []
        if recall < 0.50:
            issues.append(f"low recall ({recall:.1%})")
        if precision < 0.50:
            issues.append(f"low precision ({precision:.1%})")
        if support < 3:
            issues.append(f"insufficient samples ({support})")
        if issues:
            problematic.append({"category": cat, "issues": issues, **per_category[cat]})

    # Weighted metrics
    weighted_precision = sum(
        per_category[cat]["precision"] * per_category[cat]["support"] / total_tested
        for cat in categories
    )
    weighted_recall = sum(
        per_category[cat]["recall"] * per_category[cat]["support"] / total_tested
        for cat in categories
    )
    weighted_f1 = sum(
        per_category[cat]["f1_score"] * per_category[cat]["support"] / total_tested
        for cat in categories
    )

    # Macro metrics
    n_cats = len(categories)
    macro_precision = sum(per_category[cat]["precision"] for cat in categories) / n_cats
    macro_recall = sum(per_category[cat]["recall"] for cat in categories) / n_cats
    macro_f1 = sum(per_category[cat]["f1_score"] for cat in categories) / n_cats

    return {
        "total_tickets": len(tickets),
        "n_folds": n_folds,
        "total_tested": total_tested,
        "correct": correct,
        "accuracy": round(accuracy, 4),
        "avg_confidence": round(avg_confidence, 4),
        "avg_response_time_ms": round(avg_time * 1000, 1),
        "weighted_precision": round(weighted_precision, 4),
        "weighted_recall": round(weighted_recall, 4),
        "weighted_f1": round(weighted_f1, 4),
        "macro_precision": round(macro_precision, 4),
        "macro_recall": round(macro_recall, 4),
        "macro_f1": round(macro_f1, 4),
        "method_distribution": dict(method_counts),
        "per_category": per_category,
        "problematic_categories": problematic,
        "confusion_matrix": {a: dict(p) for a, p in confusion.items()},
    }


# ── Display ───────────────────────────────────────────────────

def print_results(results: dict, benchmark: bool = False):
    """Print formatted evaluation results."""
    r = results

    # ── Global results ─────────────────────────────────────────
    print(f"\n{'=' * 70}")
    print("📊 GLOBAL RESULTS")
    print(f"{'=' * 70}")
    print(f"\n   Total Dataset:       {r['total_tickets']} tickets")
    print(f"   Cross-Validation:    {r['n_folds']}-fold stratified")
    print(f"   Classifier Method:   Hybrid (vector + keyword fallback)")
    print(f"   Confidence Threshold: {CONFIDENCE_THRESHOLD:.0%}")
    print(f"\n   ✅ Accuracy:            {r['accuracy']:.1%}  ({r['correct']}/{r['total_tested']})")
    print(f"   📈 Avg Confidence:      {r['avg_confidence']:.1%}")
    print(f"   ⏱  Avg Response Time:   {r['avg_response_time_ms']:.1f} ms")
    print(f"   🏋️  Weighted F1-Score:   {r['weighted_f1']:.3f}")
    print(f"   📐 Macro F1-Score:      {r['macro_f1']:.3f}")

    # ── Benchmark comparison ───────────────────────────────────
    if benchmark:
        diff = r["accuracy"] - BENCHMARK_ACCURACY
        if diff >= 0:
            print(f"\n   📊 vs Benchmark ({BENCHMARK_ACCURACY:.0%}): +{diff:.1%} ✅")
        else:
            print(f"\n   📊 vs Benchmark ({BENCHMARK_ACCURACY:.0%}): {diff:.1%} ⚠️")

    # ── Method distribution ────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("📊 CLASSIFICATION METHODS")
    print(f"{'─' * 70}")
    for method, count in sorted(r["method_distribution"].items(), key=lambda x: -x[1]):
        pct = count / r["total_tested"] * 100
        print(f"   {method:35s} → {count:4d} ({pct:5.1f}%)")

    # ── Per-category metrics ───────────────────────────────────
    print(f"\n{'─' * 70}")
    print("📊 PER-CATEGORY METRICS")
    print(f"{'─' * 70}")
    print(f"\n{'Category':>12s} {'Precision':>10s} {'Recall':>10s} {'F1-Score':>10s} {'Support':>8s} {'Status':>10s}")
    print(f"{'─' * 12} {'─' * 10} {'─' * 10} {'─' * 10} {'─' * 8} {'─' * 10}")

    for cat in sorted(r["per_category"].keys()):
        m = r["per_category"][cat]
        # Determine status
        if m["f1_score"] >= 0.80:
            status = "✅"
        elif m["f1_score"] >= 0.50:
            status = "⚠️"
        else:
            status = "❌"
        print(f"{cat:>12s} {m['precision']:>10.3f} {m['recall']:>10.3f} {m['f1_score']:>10.3f} {m['support']:>8d} {status:>10s}")

    print(f"{'─' * 12} {'─' * 10} {'─' * 10} {'─' * 10} {'─' * 8} {'─' * 10}")
    print(f"{'Weighted Avg':>12s} {r['weighted_precision']:>10.3f} {r['weighted_recall']:>10.3f} {r['weighted_f1']:>10.3f} {r['total_tested']:>8d}")

    # ── Confusion matrix ───────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("📊 CONFUSION MATRIX (rows=actual, cols=predicted)")
    print(f"{'─' * 70}")

    categories = sorted(r["per_category"].keys()) + ["UNKNOWN"]
    header = "".join(f"{c:>10s}" for c in categories)
    print(f"\n{'':>12s}{header}")
    print(f"{'─' * 12}{'─' * 10 * len(categories)}")
    for a in categories:
        row_data = r["confusion_matrix"].get(a, {})
        row = "".join(f"{row_data.get(p, 0):>10d}" for p in categories)
        print(f"{a:>12s}{row}")

    # ── Problematic categories ─────────────────────────────────
    if r["problematic_categories"]:
        print(f"\n{'─' * 70}")
        print("⚠️  PROBLEMATIC CATEGORIES — Needs attention")
        print(f"{'─' * 70}")
        for p in r["problematic_categories"]:
            issues_str = ", ".join(p["issues"])
            print(f"\n   ❌ {p['category']}")
            print(f"      Issues: {issues_str}")
            print(f"      Precision: {p['precision']:.3f} | Recall: {p['recall']:.3f} | F1: {p['f1_score']:.3f} | Support: {p['support']}")
    else:
        print(f"\n{'─' * 70}")
        print("✅ No problematic categories detected")
        print(f"{'─' * 70}")

    # ── Recommendations ────────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("💡 RECOMMENDATIONS")
    print(f"{'─' * 70}")

    recommendations = []

    if r["accuracy"] < 0.60:
        recommendations.append("🔴 Critical: Accuracy below 60%. Consider:")
        recommendations.append("   - Reviewing category definitions with the client")
        recommendations.append("   - Adding more training tickets per category")
        recommendations.append("   - Fine-tuning the embedding model on domain-specific data")
    elif r["accuracy"] < 0.75:
        recommendations.append("🟡 Accuracy between 60-75%. Consider:")
        recommendations.append("   - Adding more tickets to weak categories")
        recommendations.append("   - Reviewing keyword patterns for categories with low recall")
        recommendations.append("   - Adjusting confidence threshold")
    else:
        recommendations.append("🟢 Accuracy above 75%. The classifier performs well with this data.")

    if r["avg_response_time_ms"] > 500:
        recommendations.append(f"⏱  Response time ({r['avg_response_time_ms']:.0f} ms) is high. Consider:")
        recommendations.append("   - Using a lighter embedding model")
        recommendations.append("   - Reducing n_results in vector search")
        recommendations.append("   - Moving to ChromaDB client-server mode")

    if r["macro_f1"] < 0.50:
        recommendations.append("📐 Low macro F1 indicates class imbalance. Consider:")
        recommendations.append("   - Collecting more tickets for underrepresented categories")
        recommendations.append("   - Using class weights during evaluation")

    for rec in recommendations:
        print(f"   {rec}")

    print(f"\n{'=' * 70}\n")


# ── Main ──────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Evaluate AEGIS classifier accuracy with real customer data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --file tickets_cliente.csv
  %(prog)s --file tickets_cliente.csv --benchmark
  %(prog)s --file tickets_cliente.json --folds 10
  %(prog)s --file tickets_cliente.csv --output report.json
        """,
    )
    parser.add_argument(
        "--file", "-f",
        required=True,
        help="Path to CSV or JSON file with ticket data",
    )
    parser.add_argument(
        "--folds", "-k",
        type=int,
        default=5,
        help="Number of cross-validation folds (default: 5)",
    )
    parser.add_argument(
        "--benchmark", "-b",
        action="store_true",
        help=f"Compare results against current benchmark ({BENCHMARK_ACCURACY:.0%} accuracy)",
    )
    parser.add_argument(
        "--output", "-o",
        help="Save results as JSON to this file",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible folds (default: 42)",
    )

    args = parser.parse_args()

    # ── Load data ──────────────────────────────────────────────
    filepath = Path(args.file)
    if not filepath.exists():
        print(f"❌ File not found: {filepath}")
        sys.exit(1)

    ext = filepath.suffix.lower()
    if ext == ".csv":
        print(f"📂 Loading CSV: {filepath}")
        tickets = load_from_csv(filepath)
    elif ext == ".json":
        print(f"📂 Loading JSON: {filepath}")
        tickets = load_from_json(filepath)
    else:
        print(f"❌ Unsupported file format: {ext}")
        sys.exit(1)

    if not tickets:
        print("❌ No valid tickets found in file.")
        sys.exit(1)

    if len(tickets) < args.folds:
        print(f"❌ Not enough tickets ({len(tickets)}) for {args.folds}-fold cross-validation.")
        print(f"   Use --folds {len(tickets)} or collect more data.")
        sys.exit(1)

    print(f"✅ Loaded {len(tickets)} tickets from {filepath.name}")

    # ── Run cross-validation ───────────────────────────────────
    random.seed(args.seed)
    results = run_cross_validation(tickets, n_folds=args.folds)

    # ── Print results ──────────────────────────────────────────
    print_results(results, benchmark=args.benchmark)

    # ── Save to file ───────────────────────────────────────────
    if args.output:
        output_path = Path(args.output)
        # Add benchmark comparison if requested
        output_results = dict(results)
        if args.benchmark:
            output_results["benchmark_accuracy"] = BENCHMARK_ACCURACY
            output_results["vs_benchmark"] = round(results["accuracy"] - BENCHMARK_ACCURACY, 4)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_results, f, indent=2, ensure_ascii=False)
        print(f"💾 Results saved to: {output_path}")


if __name__ == "__main__":
    main()
