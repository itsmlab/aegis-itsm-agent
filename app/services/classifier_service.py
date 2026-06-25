"""
AEGIS SaaS — Multi-tenant classifier service.
Wraps the existing classifier.py logic with per-tenant ChromaDB collections.
"""

from pathlib import Path
from typing import Optional
from threading import Lock

import sys
import io

# Suppress classifier init prints during import
_old_stdout = sys.stdout
sys.stdout = io.StringIO()

from classifier import (
    load_dataset_from_csv, create_collection, load_tickets_to_db,
    classify_ticket, get_statistics, SAMPLE_TICKETS, KEYWORD_PATTERNS,
    model as embedding_model, client as chroma_client,
)

sys.stdout = _old_stdout

from app.config import settings
from app.logging_config import get_logger, metrics_collector

logger = get_logger(__name__)


class ClassifierService:
    """
    Manages per-tenant ChromaDB collections for L1/L2 ticket classification.

    Each tenant gets its own collection named "tickets_{tenant_id}".
    Collections are cached in memory to avoid recreating them on every request.
    """

    def __init__(self):
        self._collections: dict[str, object] = {}
        self._lock = Lock()
        self._dataset = self._load_dataset()
        logger.info("Classifier service initialized", extra={
            "total_tickets": len(self._dataset),
            "categories": list(set(t["category"] for t in self._dataset)),
            "model": settings.EMBEDDING_MODEL,
        })

    def _load_dataset(self) -> list[dict]:
        """Load the ticket dataset (CSV or sample tickets)."""
        dataset = load_dataset_from_csv(settings.DATASET_PATH)
        if not dataset:
            logger.warning("Dataset CSV not found, using built-in sample tickets", extra={
                "path": settings.DATASET_PATH,
            })
            dataset = SAMPLE_TICKETS
        return dataset

    def _get_or_create_collection(self, tenant_id: str):
        """Get or create a ChromaDB collection for the given tenant.

        Thread-safe: uses double-checked locking to protect the _collections
        dict so that two concurrent requests for the same new tenant don't
        race on collection creation.
        """
        # Fast path: already cached (no lock needed for reads)
        collection = self._collections.get(tenant_id)
        if collection is not None:
            return collection

        # Slow path: create collection under lock
        with self._lock:
            # Double-check: another thread may have created it while we waited
            collection = self._collections.get(tenant_id)
            if collection is not None:
                return collection

            collection_name = f"tickets_{tenant_id}"
            collection = chroma_client.get_or_create_collection(name=collection_name)
            # Only load seed data if the collection is empty (newly created)
            if collection.count() == 0:
                load_tickets_to_db(self._dataset, collection)
                logger.info("Created new collection for tenant", extra={
                    "tenant_id": tenant_id,
                    "collection": collection_name,
                    "tickets_loaded": len(self._dataset),
                })
            self._collections[tenant_id] = collection
            return collection

    def classify(self, tenant_id: str, text: str) -> dict:
        """
        Classify a ticket description for the given tenant.

        Returns the same dict as classifier.classify_ticket():
          category, confidence, similar_tickets, method, suggested_resolution, etc.
        """
        import time
        start = time.time()

        collection = self._get_or_create_collection(tenant_id)
        result = classify_ticket(text, collection)

        latency = time.time() - start
        category = result.get("category", "UNKNOWN")
        confidence = result.get("confidence", 0.0)

        # Record metrics
        metrics_collector.record_classification(category=category, confidence=confidence)

        logger.info("Ticket classified", extra={
            "tenant_id": tenant_id,
            "category": category,
            "confidence": round(confidence, 4),
            "method": result.get("method", "unknown"),
            "latency_ms": round(latency * 1000, 2),
        })

        return result

    def get_stats(self, tenant_id: str) -> dict:
        """Get classifier statistics for the given tenant."""
        collection = self._get_or_create_collection(tenant_id)
        return get_statistics(collection)

    def get_global_stats(self) -> dict:
        """Get global classifier statistics (across all tenants)."""
        return {
            "total_tickets": len(self._dataset),
            "categories": list(set(t["category"] for t in self._dataset)),
            "model": settings.EMBEDDING_MODEL,
            "threshold": settings.CLASSIFIER_CONFIDENCE_THRESHOLD,
        }


# Singleton
classifier_service = ClassifierService()
