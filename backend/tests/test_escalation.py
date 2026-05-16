import pytest
from app.pipeline.escalation import check_escalation
from app.schemas.pipeline import ClassificationResult, EnrichmentResult


def _cls(category="Bug Report", score=0.90):
    return ClassificationResult(category=category, priority="High", confidence_score=score)


def _enrich(identifiers=None):
    return EnrichmentResult(
        core_issue="Test issue.",
        identifiers=identifiers or {},
        urgency_signal="Test urgency.",
    )


def test_low_confidence_triggers_escalation():
    flag, reason = check_escalation("some message", _cls(score=0.65), _enrich())
    assert flag is True
    assert "65%" in reason or "0.65" in reason or "threshold" in reason.lower()


def test_confidence_at_threshold_does_not_escalate():
    flag, reason = check_escalation("some message", _cls(score=0.70), _enrich())
    assert flag is False


def test_outage_keyword_triggers_escalation():
    msg = "The service is down for all users since 3pm."
    flag, reason = check_escalation(msg, _cls(), _enrich())
    assert flag is True
    assert "down for all users" in reason


def test_multiple_users_keyword_triggers_escalation():
    msg = "Dashboard stopped loading — multiple users affected."
    flag, reason = check_escalation(msg, _cls(), _enrich())
    assert flag is True


def test_billing_discrepancy_above_threshold_escalates():
    enrich = _enrich(identifiers={"discrepancy": "$260"})
    flag, reason = check_escalation("invoice issue", _cls(category="Billing Issue"), enrich)
    assert flag is True
    assert "260" in reason


def test_billing_discrepancy_below_threshold_does_not_escalate():
    enrich = _enrich(identifiers={"discrepancy": "$50"})
    flag, reason = check_escalation("invoice issue", _cls(category="Billing Issue"), enrich)
    assert flag is False


def test_incident_category_always_escalates():
    flag, reason = check_escalation("minor incident", _cls(category="Incident / Outage", score=0.95), _enrich())
    assert flag is True
    assert "auto-escalates" in reason


def test_clean_message_does_not_escalate():
    flag, reason = check_escalation(
        "Can you add a dark mode feature?",
        _cls(category="Feature Request", score=0.92),
        _enrich(),
    )
    assert flag is False
    assert reason is None
