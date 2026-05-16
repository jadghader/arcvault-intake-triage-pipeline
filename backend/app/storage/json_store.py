import json
from pathlib import Path
from app.config import settings
from app.schemas.pipeline import ProcessedRecord


def _output_path() -> Path:
    path = Path(settings.output_dir) / "processed_records.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def load_records() -> list[dict]:
    path = _output_path()
    if not path.exists():
        return []
    with open(path) as f:
        return json.load(f)


def append_record(record: ProcessedRecord) -> None:
    records = load_records()
    records.append(record.model_dump())
    with open(_output_path(), "w") as f:
        json.dump(records, f, indent=2)
