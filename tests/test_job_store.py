import json

from app.core.job_store import load_job, save_job, save_profiles
from app.core.models import ColumnMapping, ConnectionProfile, EtlJob, TableMapping


def test_job_round_trip(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("app.core.job_store.config_dir", lambda: tmp_path)
    job = EtlJob(
        "Example",
        "people.csv",
        "local",
        [
            TableMapping(
                "people",
                "public",
                "people",
                [ColumnMapping("Name", "name", transform="trim_string", constant_value="fallback")],
            )
        ],
    )
    path = save_job(job)
    loaded = load_job(path)
    assert loaded.name == "Example"
    loaded_mapping = loaded.table_mappings[0].column_mappings[0]
    assert loaded_mapping.target_column == "name"
    assert loaded_mapping.source_column == "Name"
    assert loaded_mapping.transform == "trim_string"
    assert loaded_mapping.constant_value == "fallback"


def test_load_job_with_legacy_mapping_fields(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("app.core.job_store.config_dir", lambda: tmp_path)
    job_path = tmp_path / "jobs" / "legacy.json"
    job_path.parent.mkdir(parents=True, exist_ok=True)
    job_path.write_text(
        json.dumps(
            {
                "name": "Legacy",
                "source_file_path": "people.csv",
                "connection_profile_name": "local",
                "table_mappings": [
                    {
                        "source_sheet": "people",
                        "target_schema": "public",
                        "target_table": "people",
                        "column_mappings": [{"source_column": "Name", "target_column": "name"}],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    loaded = load_job(job_path)
    mapping = loaded.table_mappings[0].column_mappings[0]
    assert mapping.transform is None
    assert mapping.constant_value is None


def test_profiles_file_never_persists_password(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("app.core.job_store.config_dir", lambda: tmp_path)
    profiles = [
        ConnectionProfile(
            name="local",
            host="localhost",
            port=5432,
            database="etl",
            username="etl_user",
            password_key="profile:etl_user@localhost/etl",
        )
    ]
    save_profiles(profiles)

    content = (tmp_path / "connection_profiles.json").read_text(encoding="utf-8")
    assert "password" not in content.replace("password_key", "")
