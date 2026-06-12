from app.core.mapping import (
    mapping_complete,
    normalize_name,
    required_columns,
    source_options_for_sheet,
    suggest_column_mappings,
    target_columns_for_mapping,
    update_column_mapping,
)
from app.core.models import ColumnDefinition, ColumnMapping, SourceSheet, TableDefinition, TableMapping


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


def test_required_columns_treat_constant_value_as_supplied() -> None:
    table = TableDefinition(
        "public",
        "people",
        [
            ColumnDefinition("public", "people", "name", "TEXT", False, False),
            ColumnDefinition("public", "people", "city", "TEXT", False, False),
        ],
    )
    mappings = [
        ColumnMapping(source_column="Name", target_column="name"),
        ColumnMapping(source_column=None, target_column="city", transform="constant_value", constant_value="NYC"),
    ]
    assert required_columns(table, mappings) == []
    assert mapping_complete(table, TableMapping("people", "public", "people", mappings))


def test_target_columns_for_mapping_excludes_identity_and_generated() -> None:
    table = TableDefinition(
        "public",
        "people",
        [
            ColumnDefinition("public", "people", "id", "INTEGER", False, False, is_identity=True),
            ColumnDefinition("public", "people", "audit", "TEXT", True, False, is_generated=True),
            ColumnDefinition("public", "people", "name", "TEXT", False, False),
        ],
    )
    assert [column.name for column in target_columns_for_mapping(table)] == ["name"]


def test_source_options_for_sheet_returns_headers() -> None:
    sheet = SourceSheet("people", ["Name", "Age", ""], 1)
    assert source_options_for_sheet(sheet) == ["Name", "Age"]


def test_update_column_mapping_returns_new_mapping_without_mutation() -> None:
    original = TableMapping(
        "people",
        "public",
        "people",
        [
            ColumnMapping(source_column="Name", target_column="name"),
            ColumnMapping(source_column="Years", target_column="age", transform="parse_integer"),
        ],
    )

    updated = update_column_mapping(
        original,
        target_column="age",
        source_column=None,
        transform="constant_value",
        constant_value="42",
    )

    assert original.column_mappings[1].source_column == "Years"
    assert original.column_mappings[1].transform == "parse_integer"
    assert len([col for col in updated.column_mappings if col.target_column == "age"]) == 1
    age_mapping = next(col for col in updated.column_mappings if col.target_column == "age")
    assert age_mapping.source_column is None
    assert age_mapping.transform == "constant_value"
    assert age_mapping.constant_value == "42"
