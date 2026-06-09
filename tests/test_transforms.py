from decimal import Decimal

import pytest

from app.core.transforms import TransformError, apply_transform, parse_boolean, parse_decimal, parse_integer


def test_parse_boolean_common_values() -> None:
    assert parse_boolean("yes") is True
    assert parse_boolean("0") is False
    assert parse_boolean("") is None


def test_parse_numeric_values() -> None:
    assert parse_integer("42") == 42
    assert parse_decimal("10.50") == Decimal("10.50")


def test_unknown_transform_raises() -> None:
    with pytest.raises(TransformError):
        apply_transform("missing", "value")
