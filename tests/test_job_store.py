from app.core.models import ColumnMapping, EtlJob, TableMapping
from app.core.job_store import load_job, save_job


def test_job_round_trip(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("app.core.job_store.config_dir", lambda: tmp_path)
    job = EtlJob("Example", "people.csv", "local", [TableMapping("people", "public", "people", [ColumnMapping("Name", "name")])])
    path = save_job(job)
    loaded = load_job(path)
    assert loaded.name == "Example"
    assert loaded.table_mappings[0].column_mappings[0].target_column == "name"
