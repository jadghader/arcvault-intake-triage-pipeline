from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import configure_env
from app.routers import pipeline, records, models

configure_env()

app = FastAPI(title="ArcVault Pipeline API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pipeline.router, prefix="/api")
app.include_router(records.router, prefix="/api/records")
app.include_router(models.router, prefix="/api/models")


@app.get("/health")
def health():
    return {"status": "ok"}
