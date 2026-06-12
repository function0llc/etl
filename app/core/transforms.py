from __future__ import annotations

import json
import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import pandas as pd


class TransformError(ValueError):
    pass


NULLISH = {"", "null", "none", "nan", "na", "n/a"}
TRUE_VALUES = {"true", "t", "yes", "y", "1"}
FALSE_VALUES = {"false", "f", "no", "n", "0"}


def is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except TypeError:
        pass
    return isinstance(value, str) and value.strip().lower() in NULLISH


def trim_string(value: Any) -> Any:
    return value.strip() if isinstance(value, str) else value


def empty_to_null(value: Any) -> Any:
    return None if is_missing(value) else value


def parse_boolean(value: Any) -> bool | None:
    if is_missing(value):
        return None
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    raise TransformError(f"cannot parse boolean: {value!r}")


def parse_integer(value: Any) -> int | None:
    if is_missing(value):
        return None
    try:
        return int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise TransformError(f"cannot parse integer: {value!r}") from exc


def parse_decimal(value: Any) -> Decimal | None:
    if is_missing(value):
        return None
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError) as exc:
        raise TransformError(f"cannot parse decimal: {value!r}") from exc


def parse_date(value: Any) -> date | None:
    if is_missing(value):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        raise TransformError(f"cannot parse date: {value!r}")
    return parsed.date()


def parse_timestamp(value: Any) -> datetime | None:
    if is_missing(value):
        return None
    if isinstance(value, datetime):
        return value
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        raise TransformError(f"cannot parse timestamp: {value!r}")
    return parsed.to_pydatetime()


def parse_uuid(value: Any) -> uuid.UUID | None:
    if is_missing(value):
        return None
    try:
        return uuid.UUID(str(value).strip())
    except ValueError as exc:
        raise TransformError(f"cannot parse UUID: {value!r}") from exc


def parse_json(value: Any) -> Any:
    if is_missing(value):
        return None
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(str(value))
    except json.JSONDecodeError as exc:
        raise TransformError(f"cannot parse JSON: {value!r}") from exc


TRANSFORMS = {
    "trim_string": trim_string,
    "empty_to_null": empty_to_null,
    "parse_boolean": parse_boolean,
    "parse_integer": parse_integer,
    "parse_decimal": parse_decimal,
    "parse_date": parse_date,
    "parse_timestamp": parse_timestamp,
    "parse_uuid": parse_uuid,
    "parse_json": parse_json,
}

UI_TRANSFORMS = [*TRANSFORMS.keys(), "constant_value"]


def apply_transform(name: str | None, value: Any, constant_value: Any = None) -> Any:
    if name == "constant_value":
        return constant_value
    if not name:
        return value
    try:
        transform = TRANSFORMS[name]
    except KeyError as exc:
        raise TransformError(f"unknown transform: {name}") from exc
    return transform(value)
