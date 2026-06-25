"""
AEGIS SaaS — RAG Knowledge Base for pattern retrieval.

Loads AEGIS_PATTERNS.md, splits it into chunks (one per pattern),
embeds them with SentenceTransformers, and stores them in ChromaDB.

Provides:
  - retrieve_similar_chunks(query, top_k): get the most relevant pattern chunks
  - init_knowledge_base(): one-time initialization (called by script)
  - get_knowledge_base_stats(): returns chunk count and status
"""

import re
import time
from pathlib import Path
from typing import Optional

import chromadb
from sentence_transformers import SentenceTransformer

from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)

# ── Constants ──────────────────────────────────────────────────

COLLECTION_NAME = "patterns_chunks"
CHROMA_PATH = settings.PROJECT_ROOT / "patterns_db"

# ── ChromaDB client (lazy init) ───────────────────────────────

_chroma_client: Optional[chromadb.PersistentClient] = None
_collection: Optional[chromadb.Collection] = None
_model: Optional[SentenceTransformer] = None


def _get_chroma_client() -> chromadb.PersistentClient:
    """Get or create the ChromaDB persistent client."""
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        logger.info("ChromaDB client initialized for patterns", extra={
            "path": str(CHROMA_PATH),
        })
    return _chroma_client


def _get_model() -> SentenceTransformer:
    """Get or create the SentenceTransformer model (same as classifier)."""
    global _model
    if _model is None:
        _model = SentenceTransformer(settings.EMBEDDING_MODEL)
        logger.info("Embedding model loaded for patterns", extra={
            "model": settings.EMBEDDING_MODEL,
        })
    return _model


# ── Chunking ───────────────────────────────────────────────────


def _chunk_patterns(text: str) -> list[dict]:
    """
    Split AEGIS_PATTERNS.md into chunks, one per pattern.

    Each pattern starts with "## Pattern AEGIS-XXX".
    Returns a list of dicts with keys: id, title, content.
    """
    # Split on pattern headers
    pattern_headers = list(re.finditer(r"^## Pattern (AEGIS-\d+)", text, re.MULTILINE))

    if not pattern_headers:
        # Fallback: if no patterns found, treat the whole file as one chunk
        logger.warning("No pattern headers found, using whole file as single chunk")
        return [{
            "id": "patterns_full",
            "title": "Full Knowledge Base",
            "content": text,
        }]

    chunks = []
    for i, match in enumerate(pattern_headers):
        pattern_id = match.group(1)
        start = match.start()

        # End is the start of the next pattern, or end of file
        if i + 1 < len(pattern_headers):
            end = pattern_headers[i + 1].start()
        else:
            end = len(text)

        chunk_text = text[start:end].strip()

        # Extract the pattern name from the header line
        header_line = text[match.start():match.end()]
        # The header is "## Pattern AEGIS-XXX", the name is on the next line "**Name:** ..."
        name_match = re.search(r"\*\*Name:\*\*\s*(.+)", chunk_text)
        title = name_match.group(1).strip() if name_match else pattern_id

        chunks.append({
            "id": pattern_id,
            "title": title,
            "content": chunk_text,
        })

    logger.info("Patterns chunked", extra={
        "chunk_count": len(chunks),
        "total_chars": len(text),
    })
    return chunks


# ── Embedding & Storage ───────────────────────────────────────


def _store_chunks(chunks: list[dict]):
    """Embed chunks and store them in ChromaDB."""
    client = _get_chroma_client()
    model = _get_model()

    # Delete existing collection if it exists, then create fresh
    try:
        client.delete_collection(COLLECTION_NAME)
    except (ValueError, chromadb.errors.NotFoundError):
        pass  # Collection doesn't exist yet


    collection = client.create_collection(name=COLLECTION_NAME)

    ids = []
    embeddings = []
    metadatas = []
    documents = []

    for chunk in chunks:
        ids.append(chunk["id"])
        text = chunk["content"]
        embedding = model.encode(text).tolist()
        embeddings.append(embedding)
        metadatas.append({
            "pattern_id": chunk["id"],
            "title": chunk["title"],
        })
        documents.append(text)

    collection.add(
        ids=ids,
        embeddings=embeddings,
        metadatas=metadatas,
        documents=documents,
    )

    logger.info("Pattern chunks stored in ChromaDB", extra={
        "collection": COLLECTION_NAME,
        "chunks_stored": len(chunks),
    })

    global _collection
    _collection = collection


# ── Public API ────────────────────────────────────────────────


def init_knowledge_base():
    """
    One-time initialization: load AEGIS_PATTERNS.md, chunk it, embed it,
    and store in ChromaDB.

    Safe to call multiple times — it will re-create the collection.
    """
    patterns_file = Path(settings.PATTERNS_FILE)
    if not patterns_file.exists():
        raise FileNotFoundError(
            f"AEGIS_PATTERNS.md not found at {settings.PATTERNS_FILE}"
        )

    text = patterns_file.read_text(encoding="utf-8")
    chunks = _chunk_patterns(text)
    _store_chunks(chunks)

    return len(chunks)


def retrieve_similar_chunks(query: str, top_k: int = 3) -> list[dict]:
    """
    Retrieve the most relevant pattern chunks for a given query.

    Args:
        query: The alert text or diagnosis query.
        top_k: Number of chunks to retrieve (default: 3).

    Returns:
        List of dicts with keys: pattern_id, title, content, distance.

    Raises:
        RuntimeError: If the knowledge base hasn't been initialized.
    """
    client = _get_chroma_client()
    model = _get_model()

    try:
        collection = client.get_collection(COLLECTION_NAME)
    except (ValueError, chromadb.errors.NotFoundError):
        raise RuntimeError(
            "Knowledge base not initialized. "
            "Run 'python scripts/init_knowledge_base.py' first."
        )


    query_embedding = model.encode(query).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["metadatas", "documents", "distances"],
    )

    chunks = []
    if results["ids"] and results["ids"][0]:
        for i, chunk_id in enumerate(results["ids"][0]):
            metadata = results["metadatas"][0][i] if results["metadatas"] else {}
            document = results["documents"][0][i] if results["documents"] else ""
            distance = results["distances"][0][i] if results["distances"] else 0.0

            chunks.append({
                "pattern_id": metadata.get("pattern_id", chunk_id),
                "title": metadata.get("title", chunk_id),
                "content": document,
                "distance": round(distance, 4),
            })

    logger.info("Pattern chunks retrieved", extra={
        "query_length": len(query),
        "chunks_retrieved": len(chunks),
        "top_distance": chunks[0]["distance"] if chunks else None,
    })

    return chunks


def get_knowledge_base_stats() -> dict:
    """Get statistics about the knowledge base."""
    client = _get_chroma_client()
    try:
        collection = client.get_collection(COLLECTION_NAME)
        count = collection.count()
        return {
            "initialized": True,
            "chunk_count": count,
            "chroma_path": str(CHROMA_PATH),
        }
    except (ValueError, chromadb.errors.NotFoundError):
        return {
            "initialized": False,
            "chunk_count": 0,
            "chroma_path": str(CHROMA_PATH),
        }


