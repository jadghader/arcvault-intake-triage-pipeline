import pytest
from app.pipeline.routing import route
from app.schemas.pipeline import ClassificationResult


def _cls(category: str, priority: str = "Medium", score: float = 0.90) -> ClassificationResult:
    return ClassificationResult(category=category, priority=priority, confidence_score=score)


def test_bug_report_routes_to_engineering():
    result = route(_cls("Bug Report"), False, None)
    assert result.destination_queue == "Engineering"
    assert result.escalation_flag is False


def test_feature_request_routes_to_product():
    result = route(_cls("Feature Request"), False, None)
    assert result.destination_queue == "Product"


def test_billing_routes_to_billing():
    result = route(_cls("Billing Issue"), False, None)
    assert result.destination_queue == "Billing"


def test_technical_question_routes_to_it():
    result = route(_cls("Technical Question"), False, None)
    assert result.destination_queue == "IT / Security"


def test_incident_routes_to_engineering():
    result = route(_cls("Incident / Outage"), False, None)
    assert result.destination_queue == "Engineering"


def test_escalation_overrides_destination():
    result = route(_cls("Bug Report"), True, "Low confidence")
    assert result.destination_queue == "Escalation"
    assert result.escalation_flag is True
    assert result.escalation_reason == "Low confidence"


def test_unknown_category_falls_back_to_escalation():
    result = route(_cls("Unknown Category"), False, None)
    assert result.destination_queue == "Escalation"


def test_routing_reason_included():
    result = route(_cls("Feature Request"), False, None)
    assert "Product" in result.routing_reason
