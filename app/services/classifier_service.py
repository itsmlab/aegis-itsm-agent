"""
AEGIS SaaS — Multi-tenant classifier service.
Wraps the existing classifier.py logic with per-tenant ChromaDB collections.
"""

from pathlib import Path
from typing import Optional

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


class ClassifierService:
    """
    Manages per-tenant ChromaDB collections for L1/L2 ticket classification.

    Each tenant gets its own collection named "tickets_{tenant_id}".
    Collections are cached in memory to avoid recreating them on every request.
    """

    def __init__(self):
        self._collections: dict[str, object] = {}
        self._dataset = self._load_dataset()

    def _load_dataset(self) -> list[dict]:
        """Load the ticket dataset (CSV or sample tickets)."""
        dataset = load_dataset_from_csv(settings.DATASET_PATH)
        if not dataset:
            print("⚠️ Using built-in sample tickets (CSV not found)")
            dataset = SAMPLE_TICKETS
        return dataset

    def _get_or_create_collection(self, tenant_id: str):
        """Get or create a ChromaDB collection for the given tenant."""
        if tenant_id not in self._collections:
            collection_name = f"tickets_{tenant_id}"
            try:
                chroma_client.delete_collection(collection_name)
            except Exception:
                pass
            collection = chroma_client.create_collection(name=collection_name)
            load_tickets_to_db(self._dataset, collection)
            self._collections[tenant_id] = collection
        return self._collections[tenant_id]

    def classify(self, tenant_id: str, text: str) -> dict:
        """
        Classify a ticket description for the given tenant.

        Returns the same dict as classifier.classify_ticket():
          category, confidence, similar_tickets, method, suggested_resolution, etc.
        """
        collection = self._get_or_create_collection(tenant_id)
        return classify_ticket(text, collection)

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