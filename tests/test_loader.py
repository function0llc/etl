from __future__ import annotations

from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine, text

from app.core.loader import load_validated_rows
from app.core.models import ValidationError, ValidationResult


def _validation_result(*, errors=None, rows=None) -> ValidationResult:
    return ValidationResult(errors=errors or [], transformed_rows=rows or {})


def test_dry_run_counts_rows_without_db_writes() -> None:
    engine = Mock()
    validation = _validation_result(
        rows={
            ("people", "public", "people"): [{"name": "Ada"}, {"name": "Grace"}],
            ("teams", "public", "teams"): [{"name": "Core"}],
        }
    )

    summary = load_validated_rows(engine, validation, dry_run=True)

    assert summary.dry_run is True
    assert summary.inserted_counts == {"public.people": 2, "public.teams": 1}
    engine.begin.assert_not_called()


def test_blocking_errors_raise_before_insert() -> None:
    engine = Mock()
    validation = _validation_result(
        errors=[
            ValidationError(
                source_sheet="people",
                target_schema="public",
                target_table="people",
                row_number=2,
                source_column="name",
                target_column="name",
                original_value="",
                transformed_value=None,
                error_type="nullability",
                message="missing",
                severity="blocking",
            )
        ]
    )

    with pytest.raises(ValueError, match="blocking errors"):
        load_validated_rows(engine, validation, dry_run=False)

    engine.begin.assert_not_called()


def test_insert_success_counts_rows() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(text("create table people (name text not null)"))

    validation = _validation_result(rows={("people", "main", "people"): [{"name": "Ada"}, {"name": "Grace"}]})
    summary = load_validated_rows(engine, validation, dry_run=False)

    assert summary.dry_run is False
    assert summary.inserted_counts == {"main.people": 2}
    with engine.connect() as conn:
        count = conn.execute(text("select count(*) from people")).scalar_one()
    assert count == 2


def test_insert_failure_rolls_back_transaction() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(text("create table people (name text not null)"))
        conn.execute(text("create table audit_log (event text not null)"))

    validation = _validation_result(
        rows={
            ("people", "main", "people"): [{"name": "Ada"}],
            ("audit", "main", "audit_log"): [{"event": None}],
        }
    )

    with pytest.raises(Exception):
        load_validated_rows(engine, validation, dry_run=False)

    with engine.connect() as conn:
        people_count = conn.execute(text("select count(*) from people")).scalar_one()
        audit_count = conn.execute(text("select count(*) from audit_log")).scalar_one()
    assert people_count == 0
    assert audit_count == 0
