from pydantic import BaseModel, Field
from typing import Optional


class PipelineRequest(BaseModel):
    raw_message: str = Field(..., min_length=1)
    source: str = Field("Web Form")
    model: str = Field("claude-sonnet-4-6")


class ClassificationResult(BaseModel):
    category: str
    priority: str
    confidence_score: float


class EnrichmentResult(BaseModel):
    core_issue: str
    identifiers: dict[str, str]
    urgency_signal: str


class RoutingResult(BaseModel):
    destination_queue: str
    routing_reason: str
    escalation_flag: bool
    escalation_reason: Optional[str] = None


class ProcessedRecord(BaseModel):
    id: str
    source: str
    timestamp: str
    raw_message: str
    model_used: str
    classification: ClassificationResult
    enrichment: EnrichmentResult
    routing: RoutingResult
    summary: str


class StepEvent(BaseModel):
    step: int
    name: str
    status: str           # running | done | error
    data: Optional[dict] = None
    error: Optional[str] = None
