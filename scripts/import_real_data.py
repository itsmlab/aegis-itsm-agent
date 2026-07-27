#!/usr/bin/env python3
"""
ITSMLab — Import real customer tickets into ChromaDB for evaluation.

Reads tickets from CSV or JSON, validates the format, shows statistics,
and loads them into a ChromaDB collection for a specific tenant.

Usage:
    python scripts/import_real_data.py --file tickets_cliente.csv --tenant-id test_tenant
    python scripts/import_real_data.py --file tickets_cliente.json --tenant-id test_tenant --replace
    python scripts/import_real_data.py --file tickets_cliente.csv --tenant-id test_tenant --dry-run
"""

import argparse
import csv
import json
import sys
from pathlib import Path
from collections import Counter

# Add project root to path so we can import classifier modules
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from classifier import (
    client as chroma_client,
    model as embedding_model,
    load_tickets_to_db,
    get_statistics,
)

# ── Valid categories ──────────────────────────────────────────
VALID_CATEGORIES = {
    "ACCESS", "DATABASE", "LICENSE", "API",
    "PERFORMANCE", "NETWORK", "SECURITY", "HOWTO", "UNKNOWN",
}


# ── Loaders ───────────────────────────────────────────────────

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
            print(f"   Required: {', '.join(sorted(required_cols))}")
            print(f"   Found:    {', '.join(sorted(reader.fieldnames))}")
            sys.exit(1)

        tickets = []
        for row_num, row in enumerate(reader, start=2):  # start=2 because row 1 is header
            try:
                ticket = {
                    "id": str(row["id"]).strip(),
                    "description": str(row["description"]).strip(),
                    "resolution": str(row["resolution"]).strip(),
                    "category": str(row["category"]).strip().upper(),
                }
                if not ticket["id"]:
                    print(f"⚠️  Row {row_num}: skipping ticket with empty id")
                    continue
                if not ticket["description"]:
                    print(f"⚠️  Row {row_num}: skipping ticket with empty description (id={ticket['id']})")
                    continue
                tickets.append(ticket)
            except KeyError as e:
                print(f"❌ Row {row_num}: missing column {e}")
                sys.exit(1)

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

    required_cols = {"id", "description", "resolution", "category"}
    tickets = []
    for idx, item in enumerate(data):
        missing = required_cols - set(item.keys())
        if missing:
            print(f"❌ Item {idx}: missing required fields: {', '.join(sorted(missing))}")
            print(f"   Required: {', '.join(sorted(required_cols))}")
            sys.exit(1)

        ticket = {
            "id": str(item["id"]).strip(),
            "description": str(item["description"]).strip(),
            "resolution": str(item["resolution"]).strip(),
            "category": str(item["category"]).strip().upper(),
        }
        if not ticket["id"]:
            print(f"⚠️  Item {idx}: skipping ticket with empty id")
            continue
        if not ticket["description"]:
            print(f"⚠️  Item {idx}: skipping ticket with empty description (id={ticket['id']})")
            continue
        tickets.append(ticket)

    return tickets


# ── Validation ────────────────────────────────────────────────

def validate_tickets(tickets: list[dict]) -> dict:
    """Validate tickets and return statistics."""
    total = len(tickets)
    category_counts = Counter()
    unknown_categories = set()
    empty_resolution = 0
    short_descriptions = 0  # < 10 chars

    for t in tickets:
        cat = t["category"]
        if cat in VALID_CATEGORIES:
            category_counts[cat] += 1
        else:
            unknown_categories.add(cat)
            category_counts["UNKNOWN"] += 1

        if not t["resolution"]:
            empty_resolution += 1
        if len(t["description"]) < 10:
            short_descriptions += 1

    return {
        "total": total,
        "category_counts": dict(category_counts),
        "unknown_categories": sorted(unknown_categories),
        "empty_resolution": empty_resolution,
        "short_descriptions": short_descriptions,
    }


def print_statistics(stats: dict):
    """Print formatted statistics."""
    print(f"\n{'=' * 60}")
    print(f"📊 DATASET STATISTICS")
    print(f"{'=' * 60}")
    print(f"   Total tickets:       {stats['total']}")
    print(f"   Categories:          {len(stats['category_counts'])}")

    if stats['category_counts']:
        print(f"\n   Distribution:")
        for cat, count in sorted(stats['category_counts'].items(), key=lambda x: -x[1]):
            pct = count / stats['total'] * 100
            bar = "█" * int(pct / 2)
            print(f"     {cat:12s}: {count:4d} ({pct:5.1f}%) {bar}")

    if stats['unknown_categories']:
        print(f"\n   ⚠️  Unknown categories found: {', '.join(stats['unknown_categories'])}")
        print(f"      Valid categories: {', '.join(sorted(VALID_CATEGORIES))}")

    if stats['empty_resolution']:
        print(f"\n   ⚠️  Tickets without resolution: {stats['empty_resolution']}")

    if stats['short_descriptions']:
        print(f"   ⚠️  Very short descriptions (<10 chars): {stats['short_descriptions']}")

    print(f"{'=' * 60}\n")


# ── ChromaDB operations ───────────────────────────────────────

def get_or_create_collection(collection_name: str, replace: bool = False):
    """Get or create a ChromaDB collection."""
    if replace:
        try:
            chroma_client.delete_collection(collection_name)
            print(f"🗑️  Deleted existing collection '{collection_name}'")
        except Exception:
            pass
        collection = chroma_client.create_collection(name=collection_name)
        print(f"✅ Created new collection '{collection_name}'")
    else:
        collection = chroma_client.get_or_create_collection(name=collection_name)
        existing_count = collection.count()
        if existing_count > 0:
            print(f"📂 Collection '{collection_name}' already has {existing_count} tickets")
            print(f"   Use --replace to overwrite existing data")
        else:
            print(f"✅ Created new collection '{collection_name}'")

    return collection


# ── Main ──────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Import real customer tickets into ChromaDB for ITSMLab evaluation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --file tickets_cliente.csv --tenant-id cliente_abc
  %(prog)s --file tickets_cliente.json --tenant-id cliente_abc --replace
  %(prog)s --file tickets_cliente.csv --tenant-id test_tenant --dry-run
        """,
    )
    parser.add_argument(
        "--file", "-f",
        required=True,
        help="Path to CSV or JSON file with ticket data",
    )
    parser.add_argument(
        "--tenant-id", "-t",
        default="test_tenant",
        help="Tenant ID for the ChromaDB collection (default: test_tenant)",
    )
    parser.add_argument(
        "--replace", "-r",
        action="store_true",
        help="Replace existing data in the collection (delete and recreate)",
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Validate and show statistics without loading into ChromaDB",
    )

    args = parser.parse_args()

    # ── Resolve file path ──────────────────────────────────────
    filepath = Path(args.file)
    if not filepath.exists():
        print(f"❌ File not found: {filepath}")
        sys.exit(1)

    # ── Detect format and load ─────────────────────────────────
    ext = filepath.suffix.lower()
    if ext == ".csv":
        print(f"📂 Loading CSV: {filepath}")
        tickets = load_from_csv(filepath)
    elif ext == ".json":
        print(f"📂 Loading JSON: {filepath}")
        tickets = load_from_json(filepath)
    else:
        print(f"❌ Unsupported file format: {ext}")
        print("   Supported formats: .csv, .json")
        sys.exit(1)

    if not tickets:
        print("❌ No valid tickets found in file.")
        sys.exit(1)

    # ── Validate and show statistics ───────────────────────────
    stats = validate_tickets(tickets)
    print_statistics(stats)

    # ── Dry run: stop here ─────────────────────────────────────
    if args.dry_run:
        print("🏁 Dry run complete. No data was loaded into ChromaDB.")
        return

    # ── Confirm ────────────────────────────────────────────────
    print(f"Ready to load {stats['total']} tickets into collection 'tickets_{args.tenant_id}'")
    if not args.replace:
        print("   (use --replace to overwrite any existing data)")
    try:
        confirm = input("Continue? [Y/n]: ").strip().lower()
        if confirm not in ("", "y", "yes"):
            print("❌ Aborted by user.")
            sys.exit(0)
    except (EOFError, KeyboardInterrupt):
        print("\n❌ Aborted.")
        sys.exit(0)

    # ── Load into ChromaDB ─────────────────────────────────────
    collection_name = f"tickets_{args.tenant_id}"
    collection = get_or_create_collection(collection_name, replace=args.replace)

    load_tickets_to_db(tickets, collection)

    # ── Show final stats ───────────────────────────────────────
    final_stats = get_statistics(collection)
    print(f"\n✅ Import complete!")
    print(f"   Collection:  {collection_name}")
    print(f"   Total tickets: {final_stats['total']}")
    print(f"   Categories:  {len(final_stats['categories'])}")
    for cat, count in sorted(final_stats['categories'].items()):
        print(f"     {cat}: {count}")


if __name__ == "__main__":
    main()
