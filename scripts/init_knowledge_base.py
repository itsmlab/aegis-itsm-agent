"""
AEGIS — Knowledge Base Initialization Script.

Loads AEGIS_PATTERNS.md, chunks it into individual patterns,
embeds them with SentenceTransformers, and stores them in ChromaDB.

Usage:
    python scripts/init_knowledge_base.py

This script should be run once after deployment, or whenever
AEGIS_PATTERNS.md is updated.
"""

import sys
import time
from pathlib import Path

# Add project root to sys.path so we can import app modules
project_root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(project_root))

from app.rag.knowledge_base import init_knowledge_base, get_knowledge_base_stats


def main():
    print("=" * 60)
    print("  AEGIS — Knowledge Base Initialization")
    print("=" * 60)

    # Check if already initialized
    stats = get_knowledge_base_stats()
    if stats["initialized"]:
        print(f"\n⚠️  Knowledge base already initialized at: {stats['chroma_path']}")
        print(f"   Current chunks: {stats['chunk_count']}")
        print("   Re-initializing will replace the existing data...")

    print("\n📖 Loading AEGIS_PATTERNS.md...")
    print("🔪 Chunking patterns...")
    print("🧠 Generating embeddings...")
    print("💾 Storing in ChromaDB...")

    start = time.time()
    try:
        chunk_count = init_knowledge_base()
        elapsed = time.time() - start
        print(f"\n✅ Knowledge base initialized successfully!")
        print(f"   • Chunks stored: {chunk_count}")
        print(f"   • Time: {elapsed:.2f}s")
        print(f"   • Location: {stats['chroma_path']}")
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        print("   Make sure AEGIS_PATTERNS.md exists in the project root.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("  The orchestrator will now use RAG retrieval")
    print("  instead of sending the full knowledge base to the LLM.")
    print("=" * 60)


if __name__ == "__main__":
    main()
