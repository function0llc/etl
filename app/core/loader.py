from __future__ import annotations

import time
from typing import Callable

from sqlalchemy import Engine, MetaData, Table, insert

from app.core.models import LoadSummary, ValidationResult


CancelCallback = Callable[[], bool]


def load_validated_rows(engine: Engine, validation: ValidationResult, dry_run: bool = False, cancel_requested: CancelCallback | None = None) -> LoadSummary:
    start = time.monotonic()
    if validation.has_blocking_errors:
        raise ValueError("Cannot load rows while validation has blocking errors")
    inserted_counts: dict[str, int] = {}
    if dry_run:
        for (_, schema, table), rows in validation.transformed_rows.items():
            inserted_counts[f"{schema}.{table}"] = len(rows)
        return LoadSummary(True, inserted_counts, time.monotonic() - start, "Dry run completed; no rows inserted")

    metadata = MetaData()
    with engine.begin() as conn:
        for (_, schema, table_name), rows in validation.transformed_rows.items():
            if cancel_requested and cancel_requested():
                raise RuntimeError("Load cancelled")
            if not rows:
                inserted_counts[f"{schema}.{table_name}"] = 0
                continue
            target = Table(table_name, metadata, schema=schema, autoload_with=conn)
            conn.execute(insert(target), rows)
            inserted_counts[f"{schema}.{table_name}"] = len(rows)
    return LoadSummary(False, inserted_counts, time.monotonic() - start, "Load completed")
