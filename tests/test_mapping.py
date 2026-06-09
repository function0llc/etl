from app.core.mapping import normalize_name, required_columns, suggest_column_mappings
from app.core.models import ColumnDefinition, TableDefinition


def test_normalize_name() -> None:
    assert normalize_name(" First Name ") == "first_name"
    assert normalize_name("Plot-Number") == "plot_number"


def test_suggest_column_mappings_normalized() -> None:
    columns = [ColumnDefinition("public", "people", "first_name", "TEXT", True, False)]
    mappings = suggest_column_mappings(["First Name"], columns)
    assert mappings[0].source_column == "First Name"
    assert mappings[0].target_column == "first_name"


def test_required_columns_excludes_defaults_and_identity() -> None:
    table = TableDefinition(
        "public",
        "people",
        [
            ColumnDefinition("public", "people", "id", "INTEGER", False, False, is_identity=True),
            ColumnDefinition("public", "people", "name", "TEXT", False, False),
            ColumnDefinition("public", "people", "created_at", "TIMESTAMP", False, True),
        ],
    )
    assert [column.name for column in required_columns(table, [])] == ["name"]
