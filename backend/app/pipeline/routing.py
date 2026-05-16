from app.schemas.pipeline import ClassificationResult, RoutingResult

ROUTING_TABLE: dict[str, str] = {
    "Bug Report": "Engineering",
    "Incident / Outage": "Engineering",
    "Feature Request": "Product",
    "Technical Question": "IT / Security",
    "Billing Issue": "Billing",
}


def route(
    classification: ClassificationResult,
    escalation_flag: bool,
    escalation_reason: str | None,
) -> RoutingResult:
    if escalation_flag:
        return RoutingResult(
            destination_queue="Escalation",
            routing_reason=escalation_reason or "Escalation condition met",
            escalation_flag=True,
            escalation_reason=escalation_reason,
        )
    queue = ROUTING_TABLE.get(classification.category, "Escalation")
    return RoutingResult(
        destination_queue=queue,
        routing_reason=f"{classification.category} routes to {queue} queue",
        escalation_flag=False,
        escalation_reason=None,
    )
