# Copyright (c) 2025 Leopoldo Lara. All rights reserved.
# Licensed under the Apache License, Version 2.0.
#
"""
Aegis Ticket Classifier - L1/L2 Support Automation
Learns from historical tickets using RAG to classify and suggest resolutions
"""

import csv
import chromadb
from sentence_transformers import SentenceTransformer
from pathlib import Path
import json
import re
from collections import Counter

print("🛡️ Aegis Ticket Classifier - Initializing...")
print("=" * 50)

# ============================================
# Configuration
# ============================================

# Try to use centralized settings from app.config (SaaS mode).
# Falls back to hardcoded defaults when running standalone (CLI mode).
try:
    from app.config import settings as _app_settings
    CLASSIFIER_DB_PATH = _app_settings.CLASSIFIER_DB_PATH
    EMBEDDING_MODEL = _app_settings.EMBEDDING_MODEL
    DATASET_PATH = _app_settings.DATASET_PATH
    CONFIDENCE_THRESHOLD = _app_settings.CLASSIFIER_CONFIDENCE_THRESHOLD
except (ImportError, Exception):
    CLASSIFIER_DB_PATH = "./tickets_db"
    EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    DATASET_PATH = "tickets_dataset.csv"
    CONFIDENCE_THRESHOLD = 0.45

# ============================================
# Keyword patterns for fallback classification
# ============================================

KEYWORD_PATTERNS = [
    {
        "category": "ACCESS",
        "keywords": [
            "login", "log in", "log-in", "password", "credential", "authenticat",
            "403", "forbidden", "access denied", "access", "permission",
            "locked out", "account lock", "mfa", "multifactor", "2fa",
            "vpn access", "provision", "ad group", "active directory",
            "role", "group membership", "distribution group", "mailbox",
            "salesforce", "azure devops", "jira", "kubernetes", "rbac",
            "cannot access", "unable to access", "reset password"
        ]
    },
    {
        "category": "DATABASE",
        "keywords": [
            "database", "query", "sql", "mysql", "postgresql", "postgres",
            "mongodb", "redis", "elasticsearch", "oracle", "mariadb",
            "connection pool", "connection refused", "replication",
            "timeout", "deadlock", "tablespace", "index", "wal",
            "shard", "replica", "failover", "connection exhausted",
            "db", "pool exhausted"
        ]
    },
    {
        "category": "LICENSE",
        "keywords": [
            "license", "licence", "expired", "expir", "subscription",
            "entitlement", "creative cloud", "microsoft 365", "office 365",
            "matlab", "autodesk", "visual studio", "software license",
            "seat", "concurrent", "checkout", "trial", "compliance",
            "quota", "deployment limit"
        ]
    },
    {
        "category": "API",
        "keywords": [
            "api", "rest", "soap", "graphql", "endpoint", "webhook",
            "500", "502", "503", "bad gateway", "rate limit", "throttl",
            "token", "oauth", "authentication", "404", "route",
            "resolver", "schema", "xsd", "swagger", "openapi"
        ]
    },
    {
        "category": "PERFORMANCE",
        "keywords": [
            "slow", "latency", "performance", "timeout", "loading",
            "cpu", "memory", "disk i/o", "throughput", "bottleneck",
            "garbage collection", "heap", "jvm", "startup",
            "page load", "response time", "resource contention",
            "pool", "cache", "eviction"
        ]
    },
    {
        "category": "NETWORK",
        "keywords": [
            "network", "dns", "ping", "connectivity", "latency",
            "switch", "router", "firewall", "vpn", "tunnel",
            "ftp", "sftp", "bandwidth", "packet loss", "icmp",
            "port", "health check", "load balancer", "drops",
            "wifi", "authentication", "radius", "spf", "mx",
            "email delivery", "dmarc", "dkim"
        ]
    },
    {
        "category": "SECURITY",
        "keywords": [
            "ssl", "tls", "certificate", "security", "vulnerability",
            "patch", "antivirus", "malware", "phishing", "ransomware",
            "cve", "audit", "compliance", "pii", "data exposure",
            "firewall rule", "security group", "ssh", "threat",
            "suspicious", "infection", "scan"
        ]
    },
    {
        "category": "HOWTO",
        "keywords": [
            "how to", "how-to", "instructions", "steps", "procedure",
            "guide", "tutorial", "setup", "configure", "set up",
            "install", "forwarding", "signature", "out of office",
            "join", "meeting", "create ticket", "request",
            "access from home", "connect to", "documentation"
        ]
    }
]

# ============================================
# Initialize components
# ============================================

print("Loading embedding model...")
model = SentenceTransformer(EMBEDDING_MODEL)
print(f"✅ Model loaded: {EMBEDDING_MODEL}")

print("Connecting to ChromaDB...")
client = chromadb.PersistentClient(path=CLASSIFIER_DB_PATH)
print(f"✅ ChromaDB ready at: {CLASSIFIER_DB_PATH}")

# ============================================
# Load dataset from CSV
# ============================================

def load_dataset_from_csv(csv_path: str) -> list[dict]:
    """Load tickets from CSV file into list of dicts."""
    if not Path(csv_path).exists():
        print(f"⚠️ Dataset file not found: {csv_path}")
        print("   Falling back to sample tickets (if any)")
        return []
    
    tickets = []
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        required_cols = {"id", "description", "resolution", "category"}
        if not reader.fieldnames or not required_cols.issubset(set(reader.fieldnames)):
            missing = required_cols - set(reader.fieldnames or [])
            print(f"⚠️ CSV missing columns: {missing}")
            return []
        
        for row in reader:
            tickets.append({
                "id": str(row["id"]).strip(),
                "description": str(row["description"]).strip(),
                "resolution": str(row["resolution"]).strip(),
                "category": str(row["category"]).strip().upper()
            })
    
    print(f"📂 Loaded {len(tickets)} tickets from CSV")
    return tickets

# ============================================
# Sample tickets (fallback / demo)
# ============================================

SAMPLE_TICKETS = [
    {
        "id": "T001",
        "description": "User cannot log in, error 403 forbidden",
        "resolution": "Added user to correct AD group, cleared cache",
        "category": "ACCESS"
    },
    {
        "id": "T002", 
        "description": "Database query timeout, application slow",
        "resolution": "Added missing index on large table",
        "category": "DATABASE"
    },
    {
        "id": "T003",
        "description": "License expired for user, cannot access feature",
        "resolution": "Renewed license in license manager",
        "category": "LICENSE"
    },
    {
        "id": "T004",
        "description": "API returning 500 errors intermittently",
        "resolution": "Restarted service, cleared connection pool",
        "category": "API"
    },
    {
        "id": "T005",
        "description": "User reports slow page loads, network latency",
        "resolution": "Optimized CDN configuration",
        "category": "PERFORMANCE"
    },
    {
        "id": "T006",
        "description": "Need access to Salesforce, account not provisioned",
        "resolution": "Created account, assigned permission set",
        "category": "ACCESS"
    },
    {
        "id": "T007",
        "description": "Report generation failing, out of memory",
        "resolution": "Optimized query, increased memory limit",
        "category": "PERFORMANCE"
    }
]

# ============================================
# Functions
# ============================================

def create_collection(collection_name="tickets"):
    """Create or get a collection in ChromaDB"""
    try:
        client.delete_collection(collection_name)
    except:
        pass
    return client.create_collection(name=collection_name)

def load_tickets_to_db(tickets, collection):
    """Add tickets to vector database"""
    print(f"\nLoading {len(tickets)} tickets to ChromaDB...")
    
    for ticket in tickets:
        # Combine description and resolution for embedding
        text = f"{ticket['description']} {ticket['resolution']}"
        embedding = model.encode(text).tolist()
        
        collection.add(
            ids=[ticket["id"]],
            embeddings=[embedding],
            metadatas=[{
                "category": ticket["category"],
                "description": ticket["description"],
                "resolution": ticket["resolution"]
            }]
        )
    
    print(f"✅ Loaded {len(tickets)} tickets")

def classify_by_keywords(description: str) -> dict:
    """
    Fallback classifier using keyword matching.
    Returns category and confidence score based on keyword density.
    """
    desc_lower = description.lower()
    
    best_match = None
    best_score = 0
    
    # Track all category scores for multi-category output
    all_scores = {}
    
    for pattern in KEYWORD_PATTERNS:
        cat = pattern["category"]
        matches = sum(1 for kw in pattern["keywords"] if kw in desc_lower)
        total_kw = len(pattern["keywords"])
        # Score = ratio of matched keywords, capped and normalized
        score = matches / max(total_kw * 0.15, 1)  # normalize: ~15% match = 1.0
        score = min(score, 1.0)  # cap at 1.0
        
        all_scores[cat] = score
        
        if score > best_score:
            best_score = score
            best_match = cat
    
    if best_match and best_score >= 0.30:
        return {
            "category": best_match,
            "confidence": best_score,
            "method": "keyword_fallback",
            "all_scores": {k: v for k, v in sorted(all_scores.items(), key=lambda x: -x[1]) if v > 0}
        }
    
    return {
        "category": "UNKNOWN",
        "confidence": 0.0,
        "method": "keyword_fallback",
        "all_scores": {}
    }

def classify_ticket(description, collection, n_results=5):
    """
    Classify a new ticket using hybrid approach:
    1. Vector search (ChromaDB + sentence-transformers)
    2. If confidence < threshold, fallback to keyword matching
    3. Always return top-k similar tickets with suggested resolutions
    """
    print(f"\n🔍 Classifying: {description}")
    
    # --- STEP 1: Vector search ---
    embedding = model.encode(description).tolist()
    
    results = collection.query(
        query_embeddings=[embedding],
        n_results=n_results
    )
    
    if not results['metadatas'] or not results['metadatas'][0]:
        # Vector search failed entirely, try keyword fallback
        keyword_result = classify_by_keywords(description)
        return {
            "category": keyword_result["category"],
            "confidence": keyword_result["confidence"],
            "similar_tickets": [],
            "weighted_voting": False,
            "method": keyword_result["method"],
            "all_category_scores": keyword_result.get("all_scores", {}),
            "suggested_resolution": None
        }
    
    # --- STEP 2: Weighted voting by inverse distance ---
    categories = [m["category"] for m in results['metadatas'][0]]
    distances = results.get('distances', [None])[0]
    
    if distances and all(d is not None for d in distances):
        epsilon = 0.001
        category_weights = {}
        for cat, dist in zip(categories, distances):
            weight = 1.0 / (dist + epsilon)
            category_weights[cat] = category_weights.get(cat, 0) + weight
        
        predicted_category = max(category_weights, key=category_weights.get)
        total_weight = sum(category_weights.values())
        confidence = category_weights[predicted_category] / total_weight if total_weight > 0 else 0
        weighted_voting = True
    else:
        category_counts = Counter(categories)
        predicted_category = category_counts.most_common(1)[0][0]
        confidence = category_counts[predicted_category] / len(categories)
        weighted_voting = False
    
    # --- STEP 3: Check confidence threshold ---
    method = "vector_weighted" if weighted_voting else "vector_majority"
    
    if confidence < CONFIDENCE_THRESHOLD:
        # Try keyword fallback
        keyword_result = classify_by_keywords(description)
        if keyword_result["category"] != "UNKNOWN" and keyword_result["confidence"] >= CONFIDENCE_THRESHOLD:
            predicted_category = keyword_result["category"]
            confidence = keyword_result["confidence"]
            method = f"vector_fallback_keyword ({method} had {confidence:.1%})"
    
    # --- STEP 4: Prepare similar tickets info ---
    similar_tickets = []
    for i, metadata in enumerate(results['metadatas'][0]):
        similar_tickets.append({
            "id": results['ids'][0][i],
            "category": metadata["category"],
            "description": metadata["description"],
            "resolution": metadata["resolution"],
            "distance": distances[i] if distances else None
        })
    
    # --- STEP 5: Suggested resolution ---
    suggested_resolution = None
    if similar_tickets:
        # Pick the closest ticket of the predicted category
        for ticket in similar_tickets:
            if ticket["category"] == predicted_category:
                suggested_resolution = ticket["resolution"]
                break
        # If none found in predicted category, take closest overall
        if not suggested_resolution and similar_tickets:
            suggested_resolution = similar_tickets[0]["resolution"]
    
    # --- STEP 6: Build all category scores for multi-category output ---
    all_category_scores = {}
    if weighted_voting:
        for cat, weight in sorted(category_weights.items(), key=lambda x: -x[1]):
            all_category_scores[cat] = round(weight / total_weight, 4) if total_weight > 0 else 0
    
    return {
        "category": predicted_category,
        "confidence": confidence,
        "similar_tickets": similar_tickets,
        "weighted_voting": weighted_voting,
        "method": method,
        "all_category_scores": all_category_scores,
        "suggested_resolution": suggested_resolution
    }

def add_ticket(description, resolution, category, collection):
    """Add a new resolved ticket to the database"""
    existing = collection.get()
    next_id = len(existing['ids']) + 1
    ticket_id = f"T{next_id:03d}"
    
    ticket = {
        "id": ticket_id,
        "description": description,
        "resolution": resolution,
        "category": category
    }
    
    text = f"{description} {resolution}"
    embedding = model.encode(text).tolist()
    
    collection.add(
        ids=[ticket_id],
        embeddings=[embedding],
        metadatas=[{
            "category": category,
            "description": description,
            "resolution": resolution
        }]
    )
    
    print(f"✅ Ticket {ticket_id} added to database")
    return ticket_id

def get_statistics(collection):
    """Show database statistics"""
    stats = collection.get()
    if not stats['ids']:
        return {"total": 0, "categories": {}}
    
    categories = [m["category"] for m in stats['metadatas']]
    return {
        "total": len(stats['ids']),
        "categories": dict(Counter(categories))
    }

# ============================================
# Main demo (only runs when executed directly)
# ============================================

if __name__ == "__main__":
    
    print("\n" + "=" * 50)
    print("Loading ticket dataset...")
    print("=" * 50)
    
    # Try loading from CSV first, fall back to sample tickets
    dataset = load_dataset_from_csv(DATASET_PATH)
    if not dataset:
        print("Using built-in sample tickets instead")
        dataset = SAMPLE_TICKETS
    
    # Create collection and load tickets
    collection = create_collection()
    load_tickets_to_db(dataset, collection)
    
    print("\n" + "=" * 50)
    print("READY: Aegis Ticket Classifier (L1/L2 Support Automation)")
    print("=" * 50)
    
    # Interactive menu
    while True:
        print("\n" + "-" * 40)
        print("OPTIONS:")
        print("  1 - Classify a new ticket (L1/L2 automation)")
        print("  2 - Add a resolved ticket (teach the system)")
        print("  3 - Show statistics")
        print("  4 - Exit")
        print("-" * 40)
        
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == "1":
            description = input("\nEnter ticket description: ").strip()
            if description:
                result = classify_ticket(description, collection)
                print(f"\n{'='*50}")
                print(f"📋 CLASSIFICATION RESULT:")
                print(f"{'='*50}")
                print(f"   Category:   {result['category']}")
                print(f"   Confidence: {result['confidence']:.1%}")
                print(f"   Method:     {result['method']}")
                
                # Multi-category scores
                if result.get('all_category_scores'):
                    print(f"\n   📊 Category distribution:")
                    for cat, score in list(result['all_category_scores'].items())[:4]:
                        bar = "█" * int(score * 20)
                        pct = score * 100
                        print(f"     {cat:12s}: {pct:5.1f}% {bar}")
                
                # Suggested resolution
                if result.get('suggested_resolution'):
                    print(f"\n   💡 Suggested resolution:")
                    print(f"      {result['suggested_resolution'][:100]}")
                
                print(f"\n   🔎 Top similar tickets:")
                for ticket in result['similar_tickets']:
                    dist_str = f" [dist={ticket['distance']:.4f}]" if ticket['distance'] else ""
                    print(f"     • {ticket['id']} [{ticket['category']}]{dist_str}")
                    print(f"       {ticket['description'][:70]}")
                print(f"{'='*50}")
        
        elif choice == "2":
            print("\nEnter ticket details:")
            description = input("  Description: ").strip()
            resolution = input("  Resolution: ").strip()
            print("  Categories: ACCESS, DATABASE, LICENSE, API, PERFORMANCE, NETWORK, SECURITY, HOWTO")
            category = input("  Category: ").strip().upper()
            if description and resolution and category:
                add_ticket(description, resolution, category, collection)
        
        elif choice == "3":
            stats = get_statistics(collection)
            print(f"\n📊 DATABASE STATISTICS:")
            print(f"   Total tickets: {stats['total']}")
            print(f"   Categories:")
            for cat, count in sorted(stats['categories'].items()):
                bar = "█" * count
                print(f"     {cat:12s}: {count:3d} {bar}")
        
        elif choice == "4":
            print("\n👋 Goodbye from Aegis Ticket Classifier!")
            break
        
        else:
            print("Invalid option. Try 1, 2, 3, or 4.")
    
    print("\n💡 Tip: Run 'python orchestrator.py' for L3/L4 incident diagnosis")