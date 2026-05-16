import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator

from app.schemas.pipeline import (
    PipelineRequest,
    ProcessedRecord,
    StepEvent,
)
from app.pipeline.classification import classify
from app.pipeline.enrichment import enrich
from app.pipeline.routing import route
from app.pipeline.escalation import check_escalation
from app.pipeline.summary import generate_summary
from app.storage.json_store import append_record
from app.storage.excel_store import upsert_record


async def run_pipeline(request: PipelineRequest) -> AsyncGenerator[StepEvent, None]:
    record_id = f"msg_{uuid.uuid4().hex[:8]}"
    timestamp = datetime.now(timezone.utc).isoformat()

    # ── Step 1: Ingestion ─────────────────────────────────────────────────────
    yield StepEvent(step=1, name="ingestion", status="done", data={
        "id": record_id,
        "source": request.source,
        "timestamp": timestamp,
        "raw_message": request.raw_message[:120] + ("…" if len(request.raw_message) > 120 else ""),
    })

    # ── Step 2: Classification ────────────────────────────────────────────────
    yield StepEvent(step=2, name="classification", status="running")
    try:
        classification = await classify(request.raw_message, request.model)
        yield StepEvent(step=2, name="classification", status="done", data=classification.model_dump())
    except Exception as e:
        yield StepEvent(step=2, name="classification", status="error", error=str(e))
        return

    # ── Step 3: Enrichment ────────────────────────────────────────────────────
    yield StepEvent(step=3, name="enrichment", status="running")
    try:
        enrichment = await enrich(request.raw_message, classification, request.model)
        yield StepEvent(step=3, name="enrichment", status="done", data=enrichment.model_dump())
    except Exception as e:
        yield StepEvent(step=3, name="enrichment", status="error", error=str(e))
        return

    # ── Step 4 & 6: Escalation + Routing ─────────────────────────────────────
    yield StepEvent(step=4, name="routing", status="running")
    escalation_flag, escalation_reason = check_escalation(
        request.raw_message, classification, enrichment
    )
    routing = route(classification, escalation_flag, escalation_reason)
    yield StepEvent(step=4, name="routing", status="done", data=routing.model_dump())

    # ── Step 5: Summary ───────────────────────────────────────────────────────
    yield StepEvent(step=5, name="summary", status="running")
    try:
        summary = await generate_summary(
            request.source, classification, enrichment, routing, request.model
        )
        yield StepEvent(step=5, name="summary", status="done", data={"summary": summary})
    except Exception as e:
        yield StepEvent(step=5, name="summary", status="error", error=str(e))
        return

    # ── Assemble + persist ────────────────────────────────────────────────────
    record = ProcessedRecord(
        id=record_id,
        source=request.source,
        timestamp=timestamp,
        raw_message=request.raw_message,
        model_used=request.model,
        classification=classification,
        enrichment=enrichment,
        routing=routing,
        summary=summary,
    )
    append_record(record)
    upsert_record(record)

    yield StepEvent(step=6, name="complete", status="done", data=record.model_dump())
