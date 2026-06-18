# Copyright (c) 2025 Leopoldo Lara. All rights reserved.
# Licensed under the Apache License, Version 2.0.
#
"""
Aegis - Cross-Validation & Formal Metrics
Evaluates classifier accuracy with precision, recall, F1-score per category
"""

import sys
import os
from pathlib import Path
from collections import Counter

sys.path.insert(0, os.path.dirname(__file__))

from classifier import (
    client, model, CLASSIFIER_DB_PATH,
    create_collection, load_tickets_to_db, classify_ticket,
    classify_by_keywords, load_dataset_from_csv, DATASET_PATH
)

# ── Config ────────────────────────────────────────────────────
N_FOLDS = 5  # Number of cross-validation folds
MIN_CONFIDENCE = 0.45  # Same threshold as classifier

# ── Load dataset ──────────────────────────────────────────────
dataset = load_dataset_from_csv(DATASET_PATH)
categories = sorted(set(t["category"] for t in dataset))
total = len(dataset)

print(f"\n{'='*70}")
print(f"🛡️  CROSS-VALIDATION — {N_FOLDS}-fold on {total} tickets")
print(f"   Categories ({len(categories)}): {', '.join(categories)}")
print(f"{'='*70}\n")

# ── Fold splitting (stratified) ──────────────────────────────
import random
random.seed(42)

# Group tickets by category
by_cat = {c: [] for c in categories}
for t in dataset:
    by_cat[t["category"]].append(t)

# Build folds with stratified distribution
folds = [[] for _ in range(N_FOLDS)]
for cat, tickets in by_cat.items():
    random.shuffle(tickets)
    for i, t in enumerate(tickets):
        folds[i % N_FOLDS].append(t)

# ── Run cross-validation ─────────────────────────────────────
all_actual = []
all_predicted = []
all_confidences = []
all_methods = []

for fold_idx in range(N_FOLDS):
    print(f"\n{'─'*70}")
    print(f"📁 Fold {fold_idx + 1}/{N_FOLDS}")
    print(f"{'─'*70}")
    
    # Split: test = this fold, train = all other folds
    test_set = folds[fold_idx]
    train_set = []
    for f in range(N_FOLDS):
        if f != fold_idx:
            train_set.extend(folds[f])
    
    print(f"   Train: {len(train_set)} tickets | Test: {len(test_set)} tickets")
    
    # Train
    collection = create_collection(f"fold_{fold_idx}")
    load_tickets_to_db(train_set, collection)
    
    # Test
    fold_actual = []
    fold_predicted = []
    fold_confidences = []
    fold_methods = []
    
    for ticket in test_set:
        description = ticket["description"]
        actual = ticket["category"]
        
        result = classify_ticket(description, collection)
        predicted = result["category"]
        confidence = result["confidence"]
        method_raw = result.get("method", "unknown")
        
        # Clean method name for display
        if "vector_fallback_keyword" in method_raw:
            method = "keyword_fallback"
        else:
            method = "vector_weighted"
        
        # If UNKNOWN or low confidence → considered incorrect for metrics
        if predicted == "UNKNOWN" or confidence < MIN_CONFIDENCE:
            predicted = "UNKNOWN"
        
        fold_actual.append(actual)
        fold_predicted.append(predicted)
        fold_confidences.append(confidence)
        fold_methods.append(method)
    
    all_actual.extend(fold_actual)
    all_predicted.extend(fold_predicted)
    all_confidences.extend(fold_confidences)
    all_methods.extend(fold_methods)
    
    # Fold accuracy
    fold_correct = sum(1 for a, p in zip(fold_actual, fold_predicted) if a == p)
    fold_total = len(fold_actual)
    print(f"   ✅ Fold accuracy: {fold_correct}/{fold_total} = {fold_correct/fold_total:.1%}")

# ── Global metrics ────────────────────────────────────────────
print(f"\n{'='*70}")
print("📊 GLOBAL RESULTS")
print(f"{'='*70}")

# Overall accuracy
correct = sum(1 for a, p in zip(all_actual, all_predicted) if a == p)
total_tested = len(all_actual)
accuracy = correct / total_tested if total_tested > 0 else 0
print(f"\n   Overall Accuracy: {correct}/{total_tested} = {accuracy:.1%}")

# Average confidence
avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0
print(f"   Avg Confidence:   {avg_confidence:.1%}")

# Method distribution
method_counts = Counter(all_methods)
print(f"\n   Classification Methods:")
for m, c in method_counts.most_common():
    print(f"     • {m}: {c} ({c/total_tested:.1%})")

# ── Per-category metrics ──────────────────────────────────────
print(f"\n{'─'*70}")
print("📊 PER-CATEGORY METRICS")
print(f"{'─'*70}")

all_categories = categories + ["UNKNOWN"]
n_cats = len(all_categories)

# Build confusion matrix
confusion = {a: {p: 0 for p in all_categories} for a in all_categories}
for a, p in zip(all_actual, all_predicted):
    confusion[a][p] += 1

# Print confusion matrix
header = "".join(f"{c:>10s}" for c in all_categories)
print(f"\n{'':>12s}{header}")
print(f"{'─'*12}{'─'*10*n_cats}")
for a in all_categories:
    row = "".join(f"{confusion[a][p]:>10d}" for p in all_categories)
    print(f"{a:>12s}{row}")

# Metrics per category
print(f"\n{'Category':>12s} {'Precision':>10s} {'Recall':>10s} {'F1-Score':>10s} {'Support':>8s}")
print(f"{'─'*12} {'─'*10} {'─'*10} {'─'*10} {'─'*8}")

macro_precision = 0
macro_recall = 0
macro_f1 = 0
weighted_precision = 0
weighted_recall = 0
weighted_f1 = 0

for cat in categories:
    tp = confusion[cat][cat]
    fp = sum(confusion[a][cat] for a in all_categories if a != cat)
    fn = sum(confusion[cat][p] for p in all_categories if p != cat)
    support = sum(confusion[cat][p] for p in all_categories)
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    
    macro_precision += precision
    macro_recall += recall
    macro_f1 += f1
    weight = support / total_tested
    weighted_precision += precision * weight
    weighted_recall += recall * weight
    weighted_f1 += f1 * weight
    
    print(f"{cat:>12s} {precision:>10.3f} {recall:>10.3f} {f1:>10.3f} {support:>8d}")

# Weighted average
print(f"{'─'*12} {'─'*10} {'─'*10} {'─'*10} {'─'*8}")
print(f"{'Weighted Avg':>12s} {weighted_precision:>10.3f} {weighted_recall:>10.3f} {weighted_f1:>10.3f} {total_tested:>8d}")

# ── Method effectiveness ─────────────────────────────────────
print(f"\n{'─'*70}")
print("📊 METHOD BREAKDOWN (Cross-Validation)")
print(f"{'─'*70}")

method_results = {}
for a, p, m in zip(all_actual, all_predicted, all_methods):
    if m not in method_results:
        method_results[m] = {"correct": 0, "total": 0}
    method_results[m]["total"] += 1
    if a == p:
        method_results[m]["correct"] += 1

for m, res in sorted(method_results.items(), key=lambda x: -x[1]["total"]):
    acc = res["correct"] / res["total"] if res["total"] > 0 else 0
    print(f"   {m:35s} → {res['correct']:3d}/{res['total']:3d} = {acc:.1%}")

# ── Summary ───────────────────────────────────────────────────
print(f"\n{'='*70}")
print("📋 FINAL SUMMARY")
print(f"{'='*70}")
print(f"""
   Total Dataset:       {total} tickets
   Cross-Validation:    {N_FOLDS}-fold stratified
   Classifier Method:   Hybrid (vector + keyword fallback)
   Confidence Threshold: {MIN_CONFIDENCE:.0%}

   Accuracy:            {accuracy:.1%}
   Avg Confidence:      {avg_confidence:.1%}
   Weighted F1-Score:   {weighted_f1:.3f}
   Macro F1-Score:      {macro_f1 / n_cats:.3f}
""")
print(f"{'='*70}")
print()