# Copyright (c) 2025 Leopoldo Lara. All rights reserved.
# Licensed under the Apache License, Version 2.0.
#
"""
Aegis - Quick test for classifier accuracy
Tests the classifier with sample tickets and shows results
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from classifier import (
    client, model, CLASSIFIER_DB_PATH,
    create_collection, load_tickets_to_db, classify_ticket,
    load_dataset_from_csv, get_statistics, DATASET_PATH,
    classify_by_keywords, KEYWORD_PATTERNS
)

# Test tickets with known expected categories
TEST_TICKETS = [
    # ACCESS tests
    ("User locked out after 3 failed login attempts", "ACCESS"),
    ("Password expired need to reset for domain account", "ACCESS"),
    ("New contractor needs access to Azure DevOps", "ACCESS"),
    ("Cannot access Jira project permission denied", "ACCESS"),
    
    # DATABASE tests
    ("MySQL query taking 30 seconds to return results", "DATABASE"),
    ("PostgreSQL connection refused max connections reached", "DATABASE"),
    ("MongoDB replica set election failed", "DATABASE"),
    
    # LICENSE tests
    ("MATLAB license checkout failed no available seats", "LICENSE"),
    ("Office 365 license not showing for new user", "LICENSE"),
    ("Visual Studio license expired renewal needed", "LICENSE"),
    
    # API tests
    ("POST endpoint returning 502 bad gateway", "API"),
    ("REST API rate limit exceeded for data sync", "API"),
    ("Webhook not firing after configuration change", "API"),
    
    # PERFORMANCE tests
    ("Web application extremely slow after deployment", "PERFORMANCE"),
    ("Server CPU at 100% during normal load", "PERFORMANCE"),
    ("Database queries timing out during peak hours", "PERFORMANCE"),
    
    # NETWORK tests
    ("VPN connection dropping every 5 minutes", "NETWORK"),
    ("Cannot ping server from remote office", "NETWORK"),
    
    # SECURITY tests
    ("SSL certificate about to expire in 3 days", "SECURITY"),
    ("Antivirus detected suspicious process", "SECURITY"),
    
    # HOWTO tests
    ("How to set up email forwarding to Gmail", "HOWTO"),
    ("Instructions for connecting to WiFi on guest network", "HOWTO"),
]

# Tickets designed to test the keyword fallback (vectorial baja confianza)
FALLBACK_TICKETS = [
    # These are edge cases where vector search might fail
    ("Login failed 403 permission denied", "ACCESS"),
    ("DB slow query timeout", "DATABASE"),
    ("License expired", "LICENSE"),
]

print("=" * 60)
print("🛡️ Aegis Classifier v2 - Accuracy Test")
print("   Hybrid: Vector + Keyword Fallback")
print("=" * 60)

# Load dataset
dataset = load_dataset_from_csv(DATASET_PATH)
collection = create_collection()
load_tickets_to_db(dataset, collection)

# Show stats
stats = get_statistics(collection)
print(f"\n📊 Database: {stats['total']} tickets in {len(stats['categories'])} categories")
for cat, count in sorted(stats['categories'].items()):
    bar = "█" * count
    print(f"   {cat:12s}: {count:3d} {bar}")

# =============================
# TEST 1: Keyword fallback standalone
# =============================
print("\n" + "=" * 60)
print("🧪 TEST 1: Keyword Fallback (standalone)")
print("=" * 60)

kw_correct = 0
kw_total = 5
kw_tests = [
    ("User cannot login error 403", "ACCESS"),
    ("Slow database query causing timeout", "PERFORMANCE"),
    ("License expired for Adobe Creative Cloud", "LICENSE"),
    ("How to configure email signature", "HOWTO"),
    ("SSL certificate renewal needed", "SECURITY"),
]
for desc, expected in kw_tests:
    result = classify_by_keywords(desc)
    predicted = result["category"]
    correct_ = predicted == expected
    if correct_: kw_correct += 1
    status = "✅" if correct_ else "❌"
    print(f"  {status} [{predicted:10s}] ({result['confidence']:.1%}) ← {desc[:50]}")

print(f"\n  📊 Keyword accuracy: {kw_correct}/{kw_total} = {kw_correct/kw_total:.0%}")

# =============================
# TEST 2: Full hybrid classification
# =============================
print("\n" + "=" * 60)
print("🧪 TEST 2: Hybrid Classification (Vector + Keyword Fallback)")
print("=" * 60)

correct = 0
total = len(TEST_TICKETS)

for description, expected_cat in TEST_TICKETS:
    result = classify_ticket(description, collection)
    predicted = result['category']
    confidence = result['confidence']
    method = result['method']
    
    is_correct = predicted == expected_cat
    if is_correct:
        correct += 1
    
    status = "✅" if is_correct else "❌"
    
    # Show method indicator
    if "fallback" in method:
        method_icon = "🔤"
    elif "keyword" in method:
        method_icon = "🔤"
    else:
        method_icon = "🧠"
    
    print(f"\n{status} {method_icon} [{predicted:10s}] ({confidence:.1%}) by {method}")
    print(f"   Expected: {expected_cat}")
    print(f"   Ticket: {description[:70]}")
    
    # Show top-2 category distribution
    if result.get('all_category_scores'):
        top_cats = list(result['all_category_scores'].items())[:3]
        scores_str = " | ".join(f"{c}={s:.0%}" for c, s in top_cats)
        print(f"   Distribution: {scores_str}")
    
    # Show suggested resolution
    if result.get('suggested_resolution'):
        print(f"   💡 Resolution: {result['suggested_resolution'][:80]}")

# Summary
print("\n" + "=" * 60)
accuracy = correct / total
print(f"📊 ACCURACY: {correct}/{total} = {accuracy:.1%}")
print("=" * 60)

# =============================
# TEST 3: Edge case - unknown tickets
# =============================
print("\n" + "=" * 60)
print("🧪 TEST 3: Edge Cases (should return UNKNOWN)")
print("=" * 60)

edge_cases = [
    "What is the meaning of life",
    "Weather forecast for tomorrow",
    "I like pizza",
]

for desc in edge_cases:
    result = classify_ticket(desc, collection)
    print(f"  {('✅' if result['category'] == 'UNKNOWN' else '❌')} [{result['category']:10s}] ({result['confidence']:.1%}) ← {desc[:50]}")