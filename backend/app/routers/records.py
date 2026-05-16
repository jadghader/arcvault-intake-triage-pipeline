from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from app.storage.json_store import load_records
from app.config import settings

router = APIRouter()


@router.get("")
def list_records():
    return load_records()


@router.get("/export/excel")
def export_excel():
    path = Path(settings.output_dir) / "processed_records.xlsx"
    if not path.exists():
        raise HTTPException(status_code=404, detail="No records to export yet.")
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="arcvault_records.xlsx",
    )


@router.get("/{record_id}")
def get_record(record_id: str):
    records = load_records()
    for r in records:
        if r["id"] == record_id:
            return r
    raise HTTPException(status_code=404, detail="Record not found")
