from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from app.config.settings import config_dir
from app.core.models import ColumnMapping, ConnectionProfile, EtlJob, TableMapping


def profiles_path() -> Path:
    return config_dir() / "connection_profiles.json"


def jobs_dir() -> Path:
    path = config_dir() / "jobs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_profiles() -> list[ConnectionProfile]:
    path = profiles_path()
    if not path.exists():
        return []
    return [ConnectionProfile(**item) for item in json.loads(path.read_text(encoding="utf-8"))]


def save_profiles(profiles: list[ConnectionProfile]) -> None:
    profiles_path().write_text(json.dumps([asdict(profile) for profile in profiles], indent=2), encoding="utf-8")


def save_job(job: EtlJob) -> Path:
    safe_name = "".join(char if char.isalnum() or char in "-_" else "_" for char in job.name).strip("_") or "job"
    path = jobs_dir() / f"{safe_name}.json"
    path.write_text(json.dumps(asdict(job), indent=2, default=str), encoding="utf-8")
    return path


def load_job(path: str | Path) -> EtlJob:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    table_mappings = []
    for item in data.get("table_mappings", []):
        column_mappings = [ColumnMapping(**mapping) for mapping in item.get("column_mappings", [])]
        table_mappings.append(TableMapping(column_mappings=column_mappings, **{key: value for key, value in item.items() if key != "column_mappings"}))
    return EtlJob(table_mappings=table_mappings, **{key: value for key, value in data.items() if key != "table_mappings"})
