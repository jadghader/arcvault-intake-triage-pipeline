import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.pipeline.classification import classify
from app.pipeline.enrichment import enrich
from app.pipeline.summary import generate_summary
from app.schemas.pipeline import ClassificationResult, EnrichmentResult, RoutingResult


# ── Helpers ──────────────────────────────────────────────────────────────────

def _mock_runner_result(output):
    result = MagicMock()
    result.final_output = output
    return result


# ── Classification ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_classify_returns_classification_result():
    mock_output = MagicMock()
    mock_output.category = "Bug Report"
    mock_output.priority = "High"
    mock_output.confidence_score = 0.94

    with patch("app.pipeline.classification.Runner.run", new=AsyncMock(return_value=_mock_runner_result(mock_output))):
        result = await classify("I get a 403 error on login.", "claude-sonnet-4-6")

    assert isinstance(result, ClassificationResult)
    assert result.category == "Bug Report"
    assert result.priority == "High"
    assert result.confidence_score == 0.94


@pytest.mark.asyncio
async def test_classify_with_groq_model():
    mock_output = MagicMock()
    mock_output.category = "Incident / Outage"
    mock_output.priority = "High"
    mock_output.confidence_score = 0.92

    with patch("app.pipeline.classification.Runner.run", new=AsyncMock(return_value=_mock_runner_result(mock_output))):
        result = await classify("Dashboard down for all users.", "groq/llama-3.3-70b-versatile")

    assert result.category == "Incident / Outage"


@pytest.mark.asyncio
async def test_classify_low_confidence():
    mock_output = MagicMock()
    mock_output.category = "Technical Question"
    mock_output.priority = "Medium"
    mock_output.confidence_score = 0.62

    with patch("app.pipeline.classification.Runner.run", new=AsyncMock(return_value=_mock_runner_result(mock_output))):
        result = await classify("How do I set up SSO with Okta?", "claude-sonnet-4-6")

    assert result.confidence_score < 0.70


# ── Enrichment ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_enrich_returns_enrichment_result():
    classification = ClassificationResult(category="Billing Issue", priority="High", confidence_score=0.98)

    mock_output = MagicMock()
    mock_output.core_issue = "Customer was charged $1,240 but contracted rate is $980."
    mock_output.identifiers = {"invoice_number": "8821", "discrepancy": "260"}
    mock_output.urgency_signal = "Confirmed $260 billing discrepancy on a specific invoice."

    with patch("app.pipeline.enrichment.Runner.run", new=AsyncMock(return_value=_mock_runner_result(mock_output))):
        result = await enrich(
            "Invoice #8821 shows $1,240 but our rate is $980.",
            classification,
            "claude-sonnet-4-6",
        )

    assert isinstance(result, EnrichmentResult)
    assert result.identifiers["discrepancy"] == "260"
    assert len(result.core_issue) > 0


@pytest.mark.asyncio
async def test_enrich_empty_identifiers():
    classification = ClassificationResult(category="Feature Request", priority="Low", confidence_score=0.91)

    mock_output = MagicMock()
    mock_output.core_issue = "Customer wants a bulk export feature for audit logs."
    mock_output.identifiers = {}
    mock_output.urgency_signal = "Not urgent — feature request with no service disruption."

    with patch("app.pipeline.enrichment.Runner.run", new=AsyncMock(return_value=_mock_runner_result(mock_output))):
        result = await enrich("We'd love a bulk export for audit logs.", classification, "claude-sonnet-4-6")

    assert result.identifiers == {}


@pytest.mark.asyncio
async def test_enrich_casts_identifier_values_to_str():
    classification = ClassificationResult(category="Bug Report", priority="High", confidence_score=0.95)

    mock_output = MagicMock()
    mock_output.core_issue = "Some issue."
    mock_output.identifiers = {"error_code": 403}  # int, not str
    mock_output.urgency_signal = "Urgent."

    with patch("app.pipeline.enrichment.Runner.run", new=AsyncMock(return_value=_mock_runner_result(mock_output))):
        result = await enrich("403 error", classification, "claude-sonnet-4-6")

    assert isinstance(result.identifiers["error_code"], str)
    assert result.identifiers["error_code"] == "403"


# ── Summary ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_summary_returns_string():
    classification = ClassificationResult(category="Bug Report", priority="High", confidence_score=0.94)
    enrichment = EnrichmentResult(
        core_issue="User cannot log in due to a 403 error.",
        identifiers={"error_code": "403"},
        urgency_signal="Access is completely blocked.",
    )
    routing = RoutingResult(
        destination_queue="Engineering",
        routing_reason="Bug Report routes to Engineering queue",
        escalation_flag=False,
        escalation_reason=None,
    )

    mock_result = MagicMock()
    mock_result.final_output = "User is blocked from login due to a 403 error. Engineering should investigate the auth service."

    with patch("app.pipeline.summary.Runner.run", new=AsyncMock(return_value=mock_result)):
        result = await generate_summary("Web Form", classification, enrichment, routing, "claude-sonnet-4-6")

    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_generate_summary_escalated_record():
    classification = ClassificationResult(category="Billing Issue", priority="High", confidence_score=0.98)
    enrichment = EnrichmentResult(
        core_issue="Customer overcharged $260 on invoice #8821.",
        identifiers={"invoice_number": "8821", "discrepancy": "260"},
        urgency_signal="Confirmed billing discrepancy.",
    )
    routing = RoutingResult(
        destination_queue="Escalation",
        routing_reason="Billing discrepancy $260 exceeds $200 threshold",
        escalation_flag=True,
        escalation_reason="Billing discrepancy $260 exceeds $200 threshold",
    )

    mock_result = MagicMock()
    mock_result.final_output = "Invoice #8821 shows a $260 overcharge. This record has been escalated for human review."

    with patch("app.pipeline.summary.Runner.run", new=AsyncMock(return_value=mock_result)):
        result = await generate_summary("Support Portal", classification, enrichment, routing, "claude-sonnet-4-6")

    assert "escalated" in result.lower() or "260" in result
