from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import Engine, select, table, column

from app.core.mapping import required_columns
from app.core.models import DatabaseMetadata, TableDefinition, TableMapping, ValidationError, ValidationResult
from app.core.transforms import TransformError, apply_transform, is_missing, parse_boolean, parse_date, parse_decimal, parse_integer, parse_json, parse_timestamp, parse_uuid


INTEGER_TYPES = {"INTEGER", "BIGINT", "SMALLINT", "INT", "INT4", "INT8", "INT2"}
NUMERIC_TYPES = {"NUMERIC", "DECIMAL", "REAL", "DOUBLE PRECISION", "FLOAT"}
BOOLEAN_TYPES = {"BOOLEAN", "BOOL"}
DATE_TYPES = {"DATE"}
TIMESTAMP_TYPES = {"TIMESTAMP", "TIMESTAMP WITHOUT TIME ZONE", "TIMESTAMP WITH TIME ZONE", "DATETIME"}
UUID_TYPES = {"UUID"}
JSON_TYPES = {"JSON", "JSONB"}


def validate_job(dataset: Any, metadata: DatabaseMetadata, mappings: list[TableMapping], engine: Engine | None = None) -> ValidationResult:
    errors: list[ValidationError] = []
    transformed_rows: dict[tuple[str, str, str], list[dict[str, Any]]] = {}

    for mapping in mappings:
        table_def = metadata.tables.get((mapping.target_schema, mapping.target_table))
        if not table_def:
            errors.append(_error(mapping, 0, None, None, None, None, "table_missing", "Target table not found"))
            continue
        for required in required_columns(table_def, mapping.column_mappings):
            errors.append(_error(mapping, 0, None, required.name, None, None, "required_mapping_missing", "Required target column is unmapped"))
        frame = dataset.sheets.get(mapping.source_sheet)
        if frame is None:
            errors.append(_error(mapping, 0, None, None, None, None, "source_missing", "Source sheet/file not found"))
            continue
        rows, row_errors = _validate_table(frame, table_def, mapping)
        errors.extend(row_errors)
        transformed_rows[(mapping.source_sheet, mapping.target_schema, mapping.target_table)] = rows
        errors.extend(_validate_unique_batch(rows, table_def, mapping))
        if engine is not None:
            errors.extend(_validate_unique_conflicts(rows, table_def, mapping, engine))
            errors.extend(_validate_foreign_keys(rows, table_def, mapping, engine))
    return ValidationResult(errors=errors, transformed_rows=transformed_rows)


def export_validation_errors(errors: list[ValidationError], path: str) -> None:
    fieldnames = ["source_sheet", "target_schema", "target_table", "row_number", "source_column", "target_column", "original_value", "transformed_value", "error_type", "message", "severity"]
    with Path(path).open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for error in errors:
            writer.writerow({field: getattr(error, field) for field in fieldnames})


def _validate_table(frame: pd.DataFrame, table_def: TableDefinition, mapping: TableMapping) -> tuple[list[dict[str, Any]], list[ValidationError]]:
    columns = {column.name: column for column in table_def.columns}
    rows: list[dict[str, Any]] = []
    errors: list[ValidationError] = []
    for idx, source_row in frame.iterrows():
        output: dict[str, Any] = {}
        row_number = int(idx) + 2
        for col_map in mapping.column_mappings:
            column_def = columns.get(col_map.target_column)
            if not column_def:
                errors.append(_error(mapping, row_number, col_map.source_column, col_map.target_column, None, None, "column_missing", "Target column not found"))
                continue
            original = source_row.get(col_map.source_column) if col_map.source_column else None
            try:
                transformed = apply_transform(col_map.transform, original, col_map.constant_value)
                transformed = _coerce_by_type(transformed, column_def.data_type)
                _validate_value(transformed, column_def)
                output[column_def.name] = transformed
            except (TransformError, ValueError) as exc:
                errors.append(_error(mapping, row_number, col_map.source_column, col_map.target_column, original, None, "type_validation", str(exc)))
        for column_def in table_def.columns:
            if column_def.name in output and is_missing(output[column_def.name]) and not column_def.nullable and not column_def.has_default:
                errors.append(_error(mapping, row_number, None, column_def.name, output[column_def.name], None, "nullability", "Non-null target receives NULL/empty value"))
        rows.append(output)
    return rows, errors


def _coerce_by_type(value: Any, data_type: str) -> Any:
    normalized = data_type.upper().split("(", 1)[0]
    if is_missing(value):
        return None
    if normalized in INTEGER_TYPES:
        return parse_integer(value)
    if normalized in NUMERIC_TYPES:
        return parse_decimal(value)
    if normalized in BOOLEAN_TYPES:
        return parse_boolean(value)
    if normalized in DATE_TYPES:
        return parse_date(value)
    if normalized in TIMESTAMP_TYPES:
        return parse_timestamp(value)
    if normalized in UUID_TYPES:
        return parse_uuid(value)
    if normalized in JSON_TYPES:
        return parse_json(value)
    return value.strip() if isinstance(value, str) else value


def _validate_value(value: Any, column_def: Any) -> None:
    if value is None:
        return
    if column_def.enum_values and str(value) not in column_def.enum_values:
        raise ValueError(f"value {value!r} is not allowed for enum {column_def.name}")
    if column_def.max_length and isinstance(value, str) and len(value) > column_def.max_length:
        raise ValueError(f"string length {len(value)} exceeds max {column_def.max_length}")
    if column_def.numeric_precision and isinstance(value, Decimal):
        sign, digits, exponent = value.as_tuple()
        scale = abs(exponent) if exponent < 0 else 0
        precision = len(digits)
        if precision > column_def.numeric_precision or (column_def.numeric_scale is not None and scale > column_def.numeric_scale):
            raise ValueError("numeric precision/scale overflow")


def _validate_unique_batch(rows: list[dict[str, Any]], table_def: TableDefinition, mapping: TableMapping) -> list[ValidationError]:
    errors: list[ValidationError] = []
    for constraint in table_def.unique_constraints:
        if not all(col in rows[0] for col in constraint.columns) if rows else False:
            continue
        seen: set[tuple[Any, ...]] = set()
        for index, row in enumerate(rows, start=2):
            key = tuple(row.get(column_name) for column_name in constraint.columns)
            if any(value is None for value in key):
                continue
            if key in seen:
                errors.append(_error(mapping, index, None, ",".join(constraint.columns), key, key, "unique_batch", f"Duplicate source values for {constraint.name}"))
            seen.add(key)
    return errors


def _validate_unique_conflicts(rows: list[dict[str, Any]], table_def: TableDefinition, mapping: TableMapping, engine: Engine) -> list[ValidationError]:
    errors: list[ValidationError] = []
    target = table(table_def.name, *[column(col.name) for col in table_def.columns], schema=table_def.schema)
    with engine.connect() as conn:
        for constraint in table_def.unique_constraints:
            for index, row in enumerate(rows, start=2):
                if not all(name in row and row[name] is not None for name in constraint.columns):
                    continue
                stmt = select(*[target.c[name] for name in constraint.columns]).where(*[target.c[name] == row[name] for name in constraint.columns]).limit(1)
                if conn.execute(stmt).first():
                    errors.append(_error(mapping, index, None, ",".join(constraint.columns), None, None, "unique_conflict", f"Target already has values for {constraint.name}"))
    return errors


def _validate_foreign_keys(rows: list[dict[str, Any]], table_def: TableDefinition, mapping: TableMapping, engine: Engine) -> list[ValidationError]:
    errors: list[ValidationError] = []
    with engine.connect() as conn:
        for fk in table_def.foreign_keys:
            ref = table(fk.referred_table, *[column(col) for col in fk.referred_columns], schema=fk.referred_schema)
            for index, row in enumerate(rows, start=2):
                if not all(name in row and row[name] is not None for name in fk.columns):
                    continue
                stmt = select(*[ref.c[name] for name in fk.referred_columns]).where(*[ref.c[ref_col] == row[src_col] for src_col, ref_col in zip(fk.columns, fk.referred_columns)]).limit(1)
                if conn.execute(stmt).first() is None:
                    errors.append(_error(mapping, index, None, ",".join(fk.columns), None, None, "foreign_key", f"Referenced row not found in {fk.referred_schema}.{fk.referred_table}"))
    return errors


def _error(mapping: TableMapping, row_number: int, source_column: str | None, target_column: str | None, original: Any, transformed: Any, error_type: str, message: str) -> ValidationError:
    return ValidationError(mapping.source_sheet, mapping.target_schema, mapping.target_table, row_number, source_column, target_column, original, transformed, error_type, message)
