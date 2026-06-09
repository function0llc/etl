import pandas as pd

from app.core.models import ColumnDefinition, DatabaseMetadata, SourceDataset, SourceSheet, TableDefinition, TableMapping, ColumnMapping
from app.core.validation import validate_job


def test_validation_blocks_missing_required_mapping() -> None:
    frame = pd.DataFrame([{"Name": "Ada"}])
    dataset = SourceDataset("people.csv", "csv", {"people": frame}, {"people": SourceSheet("people", ["Name"], 1)})
    table = TableDefinition("public", "people", [ColumnDefinition("public", "people", "name", "TEXT", False, False)])
    metadata = DatabaseMetadata(["public"], {("public", "people"): table})
    result = validate_job(dataset, metadata, [TableMapping("people", "public", "people", [])])
    assert result.has_blocking_errors
    assert result.errors[0].error_type == "required_mapping_missing"


def test_validation_transforms_rows() -> None:
    frame = pd.DataFrame([{"Age": "42"}])
    dataset = SourceDataset("people.csv", "csv", {"people": frame}, {"people": SourceSheet("people", ["Age"], 1)})
    table = TableDefinition("public", "people", [ColumnDefinition("public", "people", "age", "INTEGER", True, False)])
    metadata = DatabaseMetadata(["public"], {("public", "people"): table})
    result = validate_job(dataset, metadata, [TableMapping("people", "public", "people", [ColumnMapping("Age", "age")])])
    assert not result.errors
    rows = result.transformed_rows[("people", "public", "people")]
    assert rows == [{"age": 42}]
