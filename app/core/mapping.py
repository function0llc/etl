from __future__ import annotations

import re

from app.core.models import ColumnDefinition, ColumnMapping, DatabaseMetadata, SourceSheet, TableDefinition, TableMapping


def normalize_name(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
    return re.sub(r"_+", "_", normalized).strip("_")


def suggest_table_mapping(source_sheet: SourceSheet, metadata: DatabaseMetadata, preferred_schema: str | None = None) -> TableDefinition | None:
    candidates = list(metadata.tables.values())
    if preferred_schema:
        candidates = [table for table in candidates if table.schema == preferred_schema] + [table for table in candidates if table.schema != preferred_schema]
    source_names = {source_sheet.name, source_sheet.name.lower(), normalize_name(source_sheet.name)}
    for table in candidates:
        table_names = {table.name, table.name.lower(), normalize_name(table.name)}
        if source_names & table_names:
            return table
    return None


def suggest_column_mappings(headers: list[str], columns: list[ColumnDefinition]) -> list[ColumnMapping]:
    by_exact = {header: header for header in headers}
    by_lower = {header.lower(): header for header in headers}
    by_normalized = {normalize_name(header): header for header in headers}
    mappings: list[ColumnMapping] = []
    for column in columns:
        if column.is_identity or column.is_generated:
            continue
        source = by_exact.get(column.name) or by_lower.get(column.name.lower()) or by_normalized.get(normalize_name(column.name))
        if source:
            mappings.append(ColumnMapping(source_column=source, target_column=column.name))
    return mappings


def required_columns(table: TableDefinition, mappings: list[ColumnMapping]) -> list[ColumnDefinition]:
    supplied = {mapping.target_column for mapping in mappings if mapping.source_column or mapping.transform == "constant_value"}
    return [
        column
        for column in table.columns
        if not column.nullable
        and not column.has_default
        and not column.is_identity
        and not column.is_generated
        and column.name not in supplied
    ]


def mapping_complete(table: TableDefinition, mapping: TableMapping) -> bool:
    return not required_columns(table, mapping.column_mappings)


def target_columns_for_mapping(table: TableDefinition) -> list[ColumnDefinition]:
    return [column for column in table.columns if not column.is_identity and not column.is_generated]


def source_options_for_sheet(sheet: SourceSheet) -> list[str]:
    return [header for header in sheet.headers if header]


def update_column_mapping(
    mapping: TableMapping,
    target_column: str,
    source_column: str | None,
    transform: str | None = None,
    constant_value: object | None = None,
) -> TableMapping:
    filtered = [item for item in mapping.column_mappings if item.target_column != target_column]
    filtered.append(
        ColumnMapping(
            source_column=source_column,
            target_column=target_column,
            transform=transform,
            constant_value=constant_value,
        )
    )
    return TableMapping(
        source_sheet=mapping.source_sheet,
        target_schema=mapping.target_schema,
        target_table=mapping.target_table,
        column_mappings=filtered,
    )
