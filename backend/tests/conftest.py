import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.schemas.pipeline import ClassificationResult, EnrichmentResult


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def bug_classification():
    return ClassificationResult(
        category="Bug Report", priority="High", confidence_score=0.95
    )


@pytest.fixture
def outage_classification():
    return ClassificationResult(
        category="Incident / Outage", priority="High", confidence_score=0.92
    )


@pytest.fixture
def low_confidence_classification():
    return ClassificationResult(
        category="Technical Question", priority="Low", confidence_score=0.55
    )


@pytest.fixture
def billing_enrichment():
    return EnrichmentResult(
        core_issue="Invoice shows overcharge vs contract rate.",
        identifiers={"invoice_number": "8821", "billed_amount": "$1240", "contracted_rate": "$980", "discrepancy": "$260"},
        urgency_signal="Billing discrepancy of $260 requires prompt review.",
    )


@pytest.fixture
def empty_enrichment():
    return EnrichmentResult(
        core_issue="User cannot log in.",
        identifiers={},
        urgency_signal="Access is blocked; high urgency.",
    )
