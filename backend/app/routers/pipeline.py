import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.schemas.pipeline import PipelineRequest
from app.pipeline.runner import run_pipeline

router = APIRouter()


@router.post("/run")
async def run(request: PipelineRequest):
    async def event_stream():
        async for event in run_pipeline(request):
            yield f"data: {json.dumps(event.model_dump())}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
