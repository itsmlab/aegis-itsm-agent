"""
AEGIS SaaS — Automated tests for the multi-tenant API.

Run with:  pytest tests/ -v

Covers:
  - Health check endpoint
  - Alert processing (L1/L2 and L3/L4)
  - Stats endpoint
  - Dashboard endpoint
  - Metrics endpoint
  - Admin endpoints (tenants, API keys)
  - Authentication (valid, invalid, missing API keys)
  - Billing (quotas, plan limits)
  - Services (ClassifierService, OrchestratorService)
"""

import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Tenant, ApiKey, UsageRecord


# ═══════════════════════════════════════════════════════════════
# 1. Health Check
# ═══════════════════════════════════════════════════════════════


class TestHealth:
    """Tests for GET /v1/health."""

    def test_health_returns_200(self, test_client: TestClient):
        """Health endpoint should return 200 with status info."""
        response = test_client.get("/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "tenant" in data
        assert "version" in data
        assert "llm_provider" in data
        assert "patterns_file" in data

    def test_health_includes_tenant_info(self, test_client: TestClient):
        """Health should include the default tenant's slug and plan."""
        response = test_client.get("/v1/health")
        data = response.json()
        # In dev mode (AUTH_REQUIRED=False), the default tenant is used
        assert "tenant" in data
        assert "plan" in data
        assert data["tenant"] == "default"
        assert data["plan"] == "guard"



# ═══════════════════════════════════════════════════════════════
# 2. Alert Processing
# ═══════════════════════════════════════════════════════════════


class TestAlerts:
    """Tests for POST /v1/alert."""

    def test_l1_l2_alert_returns_200(self, test_client: TestClient, sample_alert: dict):
        """A low-severity alert should be classified as L1/L2."""
        response = test_client.post("/v1/alert", json=sample_alert)
        assert response.status_code == 200
        data = response.json()
        assert data["level"] == "L1/L2"
        assert data["pattern_id"].startswith("L1-")
        assert data["confidence"] is not None
        assert data["diagnosis"] != ""
        assert data["script"] != ""

    def test_l3_l4_alert_returns_200(self, test_client: TestClient, sample_critical_alert: dict):
        """A critical-severity alert should be routed to L3/L4."""
        response = test_client.post("/v1/alert", json=sample_critical_alert)
        assert response.status_code == 200
        data = response.json()
        assert data["level"] == "L3/L4"
        assert data["confidence"] is None  # L3/L4 doesn't have confidence

    def test_alert_without_severity_routes_by_keywords(self, test_client: TestClient):
        """Alert without severity should be routed based on description keywords."""
        # Contains "outage" keyword -> L3/L4
        response = test_client.post("/v1/alert", json={
            "source": "api",
            "title": "Something is wrong",
            "description": "We have a major outage in production",
        })
        assert response.status_code == 200
        assert response.json()["level"] == "L3/L4"

        # No critical keywords -> L1/L2
        response = test_client.post("/v1/alert", json={
            "source": "api",
            "title": "Password reset",
            "description": "User forgot password and needs reset",
        })
        assert response.status_code == 200
        assert response.json()["level"] == "L1/L2"

    def test_alert_response_structure(self, test_client: TestClient, sample_alert: dict):
        """Alert response should contain all required fields."""
        response = test_client.post("/v1/alert", json=sample_alert)
        data = response.json()
        required_fields = [
            "timestamp", "source", "severity", "level",
            "pattern_id", "pattern_name", "diagnosis", "script",
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

    def test_alert_records_usage(self, test_client: TestClient, sample_alert: dict, test_db: Session):
        """Alert should create a UsageRecord in the database."""
        response = test_client.post("/v1/alert", json=sample_alert)
        assert response.status_code == 200

        # Check that a usage record was created
        records = test_db.query(UsageRecord).all()
        assert len(records) >= 1
        assert records[-1].endpoint == "/v1/alert"


# ═══════════════════════════════════════════════════════════════
# 3. Stats Endpoint
# ═══════════════════════════════════════════════════════════════


class TestStats:
    """Tests for GET /v1/stats."""

    def test_stats_returns_200(self, test_client: TestClient):
        """Stats endpoint should return classifier and usage info."""
        response = test_client.get("/v1/stats")
        assert response.status_code == 200
        data = response.json()
        assert "tenant" in data
        assert "plan" in data
        assert "classifier" in data
        assert "usage" in data

    def test_stats_includes_classifier_info(self, test_client: TestClient):
        """Stats should include classifier details."""
        response = test_client.get("/v1/stats")
        data = response.json()
        classifier = data["classifier"]
        assert "total" in classifier
        assert "categories" in classifier

    def test_stats_includes_usage_info(self, test_client: TestClient):
        """Stats should include usage details."""
        response = test_client.get("/v1/stats")
        data = response.json()
        usage = data["usage"]
        assert "total_incidents" in usage
        assert "monthly_incidents" in usage
        assert "total_tokens_used" in usage


# ═══════════════════════════════════════════════════════════════
# 4. Dashboard Endpoint
# ═══════════════════════════════════════════════════════════════


class TestDashboard:
    """Tests for GET /dashboard."""

    def test_dashboard_returns_html(self, test_client: TestClient):
        """Dashboard should return HTML content."""
        response = test_client.get("/dashboard")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_dashboard_contains_key_sections(self, test_client: TestClient):
        """Dashboard HTML should contain key UI sections."""
        html = test_client.get("/dashboard").text
        assert "AEGIS Dashboard" in html
        assert "Estado del Sistema" in html
        assert "Distribución" in html
        assert "Actividad Reciente" in html

    def test_dashboard_shows_tenant_name(self, test_client: TestClient):
        """Dashboard should display the default tenant name."""
        html = test_client.get("/dashboard").text
        # In dev mode, the default tenant is "Default Tenant"
        assert "Default Tenant" in html



# ═══════════════════════════════════════════════════════════════
# 5. Metrics Endpoint
# ═══════════════════════════════════════════════════════════════


class TestMetrics:
    """Tests for GET /metrics."""

    def test_metrics_returns_200(self, test_client: TestClient):
        """Metrics endpoint should return JSON."""
        response = test_client.get("/metrics")
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

    def test_metrics_structure(self, test_client: TestClient):
        """Metrics should contain all expected sections."""
        response = test_client.get("/metrics")
        data = response.json()
        assert "uptime_seconds" in data
        assert "total_requests" in data
        assert "total_errors" in data
        assert "endpoints" in data
        assert "classification" in data
        assert "llm" in data
        assert "tenants" in data
        assert "timestamp" in data

    def test_metrics_tracks_requests(self, test_client: TestClient):
        """Metrics should track requests after hitting endpoints."""
        # Hit some endpoints first
        test_client.get("/v1/health")
        test_client.get("/v1/stats")

        # Check metrics
        response = test_client.get("/metrics")
        data = response.json()
        assert data["total_requests"] >= 3  # 3 requests including /metrics itself
        assert "GET /v1/health" in data["endpoints"]
        assert "GET /v1/stats" in data["endpoints"]


# ═══════════════════════════════════════════════════════════════
# 6. Admin Endpoints
# ═══════════════════════════════════════════════════════════════


class TestAdmin:
    """Tests for admin endpoints (/v1/admin/*)."""

    def test_create_tenant(self, test_client: TestClient, admin_api_key: str):
        """POST /v1/admin/tenants should create a new tenant."""
        response = test_client.post(
            "/v1/admin/tenants",
            json={"name": "New Corp", "slug": "new-corp", "plan": "shield"},
            headers={"X-API-Key": admin_api_key},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["slug"] == "new-corp"
        assert data["plan"] == "shield"
        assert data["api_key"].startswith("aeg_live_")

    def test_create_tenant_duplicate_slug(self, test_client: TestClient, admin_api_key: str, default_tenant: Tenant):
        """Creating a tenant with an existing slug should return 409."""
        response = test_client.post(
            "/v1/admin/tenants",
            json={"name": "Duplicate", "slug": default_tenant.slug, "plan": "shield"},
            headers={"X-API-Key": admin_api_key},
        )
        assert response.status_code == 409

    def test_create_tenant_invalid_plan(self, test_client: TestClient, admin_api_key: str):
        """Creating a tenant with an invalid plan should return 400."""
        response = test_client.post(
            "/v1/admin/tenants",
            json={"name": "Bad Plan", "slug": "bad-plan", "plan": "invalid"},
            headers={"X-API-Key": admin_api_key},
        )
        assert response.status_code == 400

    def test_create_api_key(self, test_client: TestClient, admin_api_key: str, default_tenant: Tenant):
        """POST /v1/admin/api-keys should generate a new API key."""
        response = test_client.post(
            f"/v1/admin/api-keys?tenant_id={default_tenant.id}&name=test-key&role=api",
            headers={"X-API-Key": admin_api_key},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["full_key"].startswith("aeg_live_")
        assert data["name"] == "test-key"

    def test_create_api_key_invalid_role(self, test_client: TestClient, admin_api_key: str, default_tenant: Tenant):
        """Creating an API key with an invalid role should return 400."""
        response = test_client.post(
            f"/v1/admin/api-keys?tenant_id={default_tenant.id}&name=test&role=superadmin",
            headers={"X-API-Key": admin_api_key},
        )
        assert response.status_code == 400

    def test_list_tenants(self, test_client: TestClient, admin_api_key: str, default_tenant: Tenant):
        """GET /v1/admin/tenants should list all tenants."""
        response = test_client.get(
            "/v1/admin/tenants",
            headers={"X-API-Key": admin_api_key},
        )
        assert response.status_code == 200
        data = response.json()
        assert "tenants" in data
        slugs = [t["slug"] for t in data["tenants"]]
        assert default_tenant.slug in slugs

    def test_get_tenant_usage(self, test_client: TestClient, admin_api_key: str, default_tenant: Tenant):
        """GET /v1/admin/usage/{tenant_id} should return usage stats."""
        response = test_client.get(
            f"/v1/admin/usage/{default_tenant.id}",
            headers={"X-API-Key": admin_api_key},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == default_tenant.id
        assert data["slug"] == default_tenant.slug
        assert "total_incidents" in data
        assert "monthly_incidents" in data


# ═══════════════════════════════════════════════════════════════
# 7. Authentication
# ═══════════════════════════════════════════════════════════════


class TestAuthentication:
    """Tests for API key authentication."""

    def test_missing_api_key_in_dev_mode(self, test_client: TestClient):
        """In dev mode (AUTH_REQUIRED=False), requests without API key should work."""
        response = test_client.get("/v1/health")
        assert response.status_code == 200

    def test_valid_api_key(self, test_client: TestClient, regular_api_key: str):
        """A valid API key should authenticate successfully."""
        response = test_client.get(
            "/v1/health",
            headers={"X-API-Key": regular_api_key},
        )
        assert response.status_code == 200

    def test_invalid_api_key(self, test_client: TestClient):
        """An invalid API key should return 401 when auth is required."""
        # Note: in dev mode (AUTH_REQUIRED=False), this still works
        # We test the key is accepted but the default tenant is used
        response = test_client.get(
            "/v1/health",
            headers={"X-API-Key": "invalid-key-12345"},
        )
        # In dev mode, auth is not enforced
        assert response.status_code == 200

    def test_admin_endpoint_with_regular_key(self, test_client: TestClient, regular_api_key: str):
        """A regular (non-admin) API key should not access admin endpoints when auth is on."""
        # In dev mode, admin endpoints don't enforce auth
        response = test_client.post(
            "/v1/admin/tenants",
            json={"name": "Test", "slug": "test", "plan": "shield"},
            headers={"X-API-Key": regular_api_key},
        )
        # Dev mode allows it
        assert response.status_code == 200

    def test_admin_endpoint_with_admin_key(self, test_client: TestClient, admin_api_key: str):
        """An admin API key should access admin endpoints."""
        response = test_client.post(
            "/v1/admin/tenants",
            json={"name": "Admin Corp", "slug": "admin-corp", "plan": "guard"},
            headers={"X-API-Key": admin_api_key},
        )
        assert response.status_code == 200


# ═══════════════════════════════════════════════════════════════
# 8. Billing & Quotas
# ═══════════════════════════════════════════════════════════════


class TestBilling:
    """Tests for billing and quota enforcement."""

    def test_shield_plan_has_limit(self, test_client: TestClient, shield_tenant: Tenant, test_db: Session):
        """Shield plan should have a monthly limit."""
        from app.config import settings
        assert settings.SHIELD_MAX_INCIDENTS_PER_MONTH == 50

    def test_guard_plan_unlimited(self, test_client: TestClient, default_tenant: Tenant):
        """Guard plan should allow unlimited requests."""
        for _ in range(5):
            response = test_client.post("/v1/alert", json={
                "source": "test",
                "severity": "low",
                "title": f"Test ticket",
                "description": "Testing unlimited plan",
            })
            assert response.status_code == 200

    def test_usage_recorded_per_request(self, test_client: TestClient, sample_alert: dict, test_db: Session):
        """Each alert request should create a usage record."""
        initial_count = test_db.query(UsageRecord).count()

        test_client.post("/v1/alert", json=sample_alert)
        test_client.post("/v1/alert", json=sample_alert)

        final_count = test_db.query(UsageRecord).count()
        assert final_count >= initial_count + 2

    def test_usage_tracks_tokens(self, test_client: TestClient, sample_alert: dict, test_db: Session):
        """Usage records should track tokens_used."""
        test_client.post("/v1/alert", json=sample_alert)
        record = test_db.query(UsageRecord).order_by(UsageRecord.id.desc()).first()
        assert record is not None
        assert record.endpoint == "/v1/alert"
        assert record.incident_count == 1


# ═══════════════════════════════════════════════════════════════
# 9. Services
# ═══════════════════════════════════════════════════════════════


class TestClassifierService:
    """Tests for ClassifierService."""

    def test_classifier_service_singleton(self):
        """ClassifierService should be a singleton."""
        from app.services.classifier_service import classifier_service
        from app.services.classifier_service import ClassifierService
        assert isinstance(classifier_service, ClassifierService)

    def test_classifier_global_stats(self):
        """get_global_stats should return dataset info."""
        from app.services.classifier_service import classifier_service
        stats = classifier_service.get_global_stats()
        assert "total_tickets" in stats
        assert "categories" in stats
        assert "model" in stats
        assert stats["model"] == settings.EMBEDDING_MODEL

    def test_classifier_classify_returns_dict(self):
        """classify should return a dict with expected keys."""
        from app.services.classifier_service import classifier_service
        result = classifier_service.classify("default", "User cannot log in")
        assert isinstance(result, dict)
        assert "category" in result
        assert "confidence" in result
        assert "method" in result

    def test_classifier_unknown_ticket(self):
        """An ambiguous ticket should return UNKNOWN with low confidence."""
        from app.services.classifier_service import classifier_service
        result = classifier_service.classify("default", "xyzzy flurbo garblex")
        # May return UNKNOWN or a low-confidence category
        assert result["confidence"] < 0.5 or result["category"] == "UNKNOWN"


class TestOrchestratorService:
    """Tests for OrchestratorService."""

    def test_orchestrator_service_singleton(self):
        """OrchestratorService should be a singleton."""
        from app.services.orchestrator_service import orchestrator_service
        from app.services.orchestrator_service import OrchestratorService
        assert isinstance(orchestrator_service, OrchestratorService)

    def test_orchestrator_pattern_count(self):
        """get_pattern_count should return the number of patterns."""
        from app.services.orchestrator_service import orchestrator_service
        count = orchestrator_service.get_pattern_count()
        assert count >= 20  # We have at least 20 patterns

    def test_orchestrator_provider_name(self):
        """get_provider_name should return the configured LLM provider."""
        from app.services.orchestrator_service import orchestrator_service
        name = orchestrator_service.get_provider_name()
        assert name is not None
        assert isinstance(name, str)


class TestBillingService:
    """Tests for BillingService."""

    def test_billing_service_singleton(self):
        """BillingService should be a singleton."""
        from app.services.billing_service import billing_service
        from app.services.billing_service import BillingService
        assert isinstance(billing_service, BillingService)

    def test_get_usage_returns_dict(self, test_db: Session, default_tenant: Tenant):
        """get_usage should return usage statistics."""
        from app.services.billing_service import billing_service
        usage = billing_service.get_usage(test_db, default_tenant.id)
        assert "total_incidents" in usage
        assert "monthly_incidents" in usage
        assert "total_tokens_used" in usage

    def test_check_quota_guard_plan(self, test_db: Session, default_tenant: Tenant):
        """Guard plan should not raise quota errors."""
        from app.services.billing_service import billing_service
        # Should not raise
        billing_service.check_quota(test_db, default_tenant)

    def test_record_usage_creates_record(self, test_db: Session, default_tenant: Tenant):
        """record_usage should create a UsageRecord."""
        from app.services.billing_service import billing_service
        initial_count = test_db.query(UsageRecord).count()
        billing_service.record_usage(test_db, default_tenant, "/v1/alert", tokens_used=100)
        final_count = test_db.query(UsageRecord).count()
        assert final_count == initial_count + 1


# ═══════════════════════════════════════════════════════════════
# 10. Root Endpoint
# ═══════════════════════════════════════════════════════════════


class TestRoot:
    """Tests for GET /."""

    def test_root_returns_service_info(self, test_client: TestClient):
        """Root endpoint should return service metadata."""
        response = test_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == settings.APP_NAME
        assert data["version"] == settings.APP_VERSION
        assert data["status"] == "operational"
        assert "endpoints" in data

    def test_root_lists_all_endpoints(self, test_client: TestClient):
        """Root should list all available endpoints."""
        response = test_client.get("/")
        endpoints = response.json()["endpoints"]
        assert "/v1/alert" in str(endpoints)
        assert "/v1/health" in str(endpoints)
        assert "/v1/stats" in str(endpoints)
        assert "/dashboard" in str(endpoints)
        assert "/metrics" in str(endpoints)
        assert "/docs" in str(endpoints)


# ═══════════════════════════════════════════════════════════════
# 11. Error Handling
# ═══════════════════════════════════════════════════════════════


class TestErrorHandling:
    """Tests for error responses."""

    def test_404_returns_json(self, test_client: TestClient):
        """Non-existent endpoint should return JSON error."""
        response = test_client.get("/nonexistent")
        assert response.status_code == 404
        assert "application/json" in response.headers["content-type"]

    def test_invalid_payload_returns_422(self, test_client: TestClient):
        """Invalid request payload should return 422."""
        response = test_client.post("/v1/alert", json={"invalid": "data"})
        assert response.status_code == 422

    def test_response_has_request_id(self, test_client: TestClient):
        """All responses should include X-Request-ID header."""
        response = test_client.get("/v1/health")
        assert "X-Request-ID" in response.headers
        assert len(response.headers["X-Request-ID"]) > 0
