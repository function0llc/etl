from decimal import Decimal

import pytest

from app.core.transforms import TRANSFORMS, UI_TRANSFORMS, TransformError, apply_transform, parse_boolean, parse_decimal, parse_integer


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


def test_constant_value_transform_applies_value() -> None:
    assert apply_transform("constant_value", "ignored", "x") == "x"


def test_ui_transforms_include_constant_value() -> None:
    assert "constant_value" in UI_TRANSFORMS


def test_ui_transforms_exist_in_registry_except_constant() -> None:
    missing = [name for name in UI_TRANSFORMS if name != "constant_value" and name not in TRANSFORMS]
    assert not missing


def test_parse_json_is_available_in_ui_transforms() -> None:
    assert "parse_json" in UI_TRANSFORMS
