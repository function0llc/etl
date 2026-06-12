# ETL Loader Architectural Implementation Plan

## Metadata

```yaml
plan_id: etl-loader-architecture-implementation
source_plan: .kilo/plans/continuation-roadmap.md
target_project: etl-loader
language_runtime: Python >=3.11
app_type: standalone PySide6 desktop application
primary_goal: make the existing MVP safe, editable, testable, and ready for end-to-end use
next_milestone_scope:
  - M1 stabilization
  - M2 editable column mappings
explicit_deferrals:
  - full streaming architecture
  - upsert/merge loading
  - staging tables
  - multi-database support
  - installer/signing/notarization
  - broad refactor away from MainWindow.state
```

## Execution Index

```yaml
execution_order:
  - id: M1-T1
    title: README and smoke checklist
    files: [README.md]
    commands: [pytest]
  - id: M1-T2
    title: State and engine lifecycle hardening
    files: [app/ui/main_window.py, app/ui/db_connection_page.py, app/ui/file_select_page.py]
    commands: [pytest, manual:python -m app.main]
  - id: M1-T3
    title: Validation/load worker lifecycle safety
    files: [app/ui/validation_page.py, app/ui/load_page.py]
    commands: [pytest, manual:python -m app.main]
  - id: M1-T4
    title: Loader transaction tests
    files: [tests/test_loader.py, app/core/loader.py]
    commands: [pytest tests/test_loader.py, pytest]
  - id: M2-T1
    title: Pure mapping helper contracts
    files: [app/core/mapping.py, tests/test_mapping.py]
    commands: [pytest tests/test_mapping.py]
  - id: M2-T2
    title: Transform registry exposure and semantics
    files: [app/core/transforms.py, tests/test_transforms.py]
    commands: [pytest tests/test_transforms.py]
  - id: M2-T3
    title: Editable ColumnMappingPage
    files: [app/ui/column_mapping_page.py]
    commands: [pytest, manual:python -m app.main]
  - id: M2-T4
    title: Edited mapping job persistence
    files: [app/core/job_store.py, tests/test_job_store.py]
    commands: [pytest tests/test_job_store.py]
  - id: M3-T1
    title: Batched validation checks and unique-batch fix
    files: [app/core/validation.py, tests/test_validation.py]
    commands: [pytest tests/test_validation.py]
  - id: M3-T2
    title: Validation UI severity feedback
    files: [app/ui/validation_page.py]
    commands: [pytest, manual:python -m app.main]
  - id: M4-T1
    title: PostgreSQL integration test harness
    files: [pyproject.toml, tests/integration/conftest.py]
    commands: [pytest, pytest -m integration]
  - id: M5-T1
    title: Transaction strategy documentation and compatibility
    files: [README.md, MEMORY.md, app/core/loader.py, tests/test_loader.py]
    commands: [pytest tests/test_loader.py, pytest]
  - id: M6-T1
    title: Large-file guardrails
    files: [app/core/file_loader.py, app/ui/file_select_page.py]
    commands: [pytest, manual:python -m app.main]
  - id: M7-T1
    title: Future editable table mapping
    files: [app/ui/table_mapping_page.py, app/core/mapping.py]
    commands: [pytest, manual:python -m app.main]
```

## Architectural Constraints

1. Keep ETL/business logic in `app/core`.
2. Keep PySide6 widgets in `app/ui`; widgets orchestrate state and core calls only.
3. Keep blocking work in `app/workers` using `QObject`, `QThread`, and Qt signals.
4. Preserve `MainWindow.state` as the current cross-page state contract unless explicitly refactoring it.
5. Never persist or log DB passwords, connection URLs containing passwords, source row values, or credentials.
6. Preserve saved profile/job compatibility unless a migration path is included.
7. Preserve load safety:
   - validation blocking errors prevent insert;
   - dry run inserts nothing;
   - insert mode rolls back active transaction on failure/cancellation.
8. Run `pytest` after core, persistence, validation, mapping, loader, or transform changes.
9. Run `python -m app.main` manual smoke test after UI changes.
10. Update `MEMORY.md` for significant architecture, persistence, validation, loading, or packaging changes.

## Qt Threading Contract

```yaml
threading_rules:
  workers_must_not:
    - read MainWindow.state directly
    - mutate MainWindow.state directly
    - update PySide widgets directly
  ui_pages_must:
    - pass only required input objects into worker constructors
    - update MainWindow.state only from main-thread signal slots
    - disable operation buttons immediately when starting worker work
    - re-enable operation buttons on finished and failed signals
    - ignore repeated clicks while a thread is running
  worker_outputs:
    - progress: Qt Signal(str)
    - finished: Qt Signal(object)
    - failed: Qt Signal(str)
  current_cancellation_limitations:
    - ValidationWorker.cancel only sets a flag and does not interrupt validate_job once running
    - LoadWorker.cancel is only checked between table batches in load_validated_rows
```

Required cleanup wiring for worker pages:

```python
worker.finished.connect(thread.quit)
worker.failed.connect(thread.quit)
worker.finished.connect(worker.deleteLater)
worker.failed.connect(worker.deleteLater)
thread.finished.connect(thread.deleteLater)
thread.finished.connect(lambda: setattr(self, "thread", None))
thread.finished.connect(lambda: setattr(self, "worker", None))
```

## MainWindow State Contract

### State keys

```python
{
    "dataset": SourceDataset,
    "profile": ConnectionProfile,
    "engine": sqlalchemy.Engine,
    "metadata": DatabaseMetadata,
    "mappings": list[TableMapping],
    "validation": ValidationResult,
}
```

### State transition matrix

| Event | Preserve | Clear or dispose |
| --- | --- | --- |
| New file selected | `profile`, `engine`, `metadata` | `mappings`, `validation` |
| New DB connection succeeds | `dataset` | dispose old `engine`; clear old `metadata`, `mappings`, `validation`; replace `profile`, `engine`, `metadata` |
| DB introspection fails after creating engine | previous known-good state | dispose failed new engine |
| Mapping edited | `dataset`, `profile`, `engine`, `metadata`, updated `mappings` | `validation` |
| App close | no user state requirement | dispose active `engine` |

### Data contracts

Use existing dataclasses in `app/core/models.py` and do not rename or remove fields in this milestone:

- `SourceDataset`
- `SourceSheet`
- `ConnectionProfile`
- `ColumnDefinition`
- `UniqueConstraint`
- `ForeignKey`
- `TableDefinition`
- `DatabaseMetadata`
- `ColumnMapping`
- `TableMapping`
- `EtlJob`
- `ValidationError`
- `ValidationResult`
- `LoadSummary`

## Target Layer Responsibilities

```text
app/main.py
  -> bootstrap logging, QApplication, MainWindow

app/ui/main_window.py
  -> page composition, shared state owner, engine disposal on close

app/ui/*_page.py
  -> render workflow pages, collect user choices, call app/core helpers, start workers

app/workers/*
  -> wrap blocking core operations and expose Qt signals only

app/core/*
  -> pure/testable ETL behavior, database operations, persistence, validation, mapping

tests/*
  -> unit tests for core behavior; optional integration tests for PostgreSQL
```

## Transform And Constant-Value Contract

`constant_value` is handled specially by `apply_transform()` and is not currently a member of `TRANSFORMS`.

```yaml
transform_rules:
  ui_transform_source: app.core.transforms.UI_TRANSFORMS
  required_ui_transforms_definition: list(TRANSFORMS.keys()) + ["constant_value"]
  parse_json_policy: include in UI_TRANSFORMS unless intentionally excluded with a code comment and test
  constant_value_precedence:
    - if transform == "constant_value", ignore source_column
    - UI may disable or clear source_column when constant_value is selected
  constant_value_typing:
    - stored as raw user-entered value in ColumnMapping.constant_value
    - passed through apply_transform
    - then coerced by validation target type rules
  empty_constant_value:
    - follows existing is_missing/nullability behavior during validation
```

Required tests:

- `apply_transform("constant_value", "ignored", "x") == "x"`
- every UI transform except `constant_value` exists in `TRANSFORMS`
- `constant_value` appears in UI transform options
- `parse_json` inclusion/exclusion is asserted according to chosen policy

## Testing Backend Rules

```yaml
normal_pytest:
  requires_postgres: false
  may_use:
    - mocks
    - fakes
    - SQLite only for generic SQLAlchemy transaction behavior
  must_not_claim_to_cover:
    - PostgreSQL introspection correctness
    - enum behavior
    - identity/generated column behavior
    - PostgreSQL unique/FK semantics
postgres_integration_tests:
  marker: integration
  command: pytest -m integration
  skip_when_unconfigured: true
  required_for:
    - db_introspection
    - real PostgreSQL insert rollback
    - unique/FK DB validation
    - enum and identity/generated metadata
credential_safety:
  - never print full ETL_TEST_POSTGRES_URL
  - never include passwords in assertion messages
  - redact URLs in failure output
  - prefer split env vars in CI
```

## Implementation Milestone 1: Stabilize End-To-End MVP

### M1-T1: README and smoke checklist

```yaml
id: M1-T1
title: README and smoke checklist
change_type: docs
depends_on: []
files:
  - README.md
  - MEMORY.md # only if workflow/architecture notes change
acceptance_tests:
  - pytest
done_when:
  - README no longer says cd etl_loader
  - setup/run/test/package commands match pyproject.toml and repo layout
  - manual smoke checklist is documented
  - all-or-nothing transaction strategy is documented as current runtime behavior
```

Required changes:

1. Replace stale `cd etl_loader` commands with commands valid for current repository root.
2. Add manual smoke checklist:
   - create virtualenv;
   - install `.[dev]`;
   - run `python -m app.main`;
   - select CSV/XLSX;
   - connect/introspect PostgreSQL;
   - review table mapping;
   - edit column mapping after M2;
   - validate;
   - dry-run;
   - insert only against disposable database.

### M1-T2: State and engine lifecycle hardening

```yaml
id: M1-T2
title: State and engine lifecycle hardening
change_type: code
depends_on: []
files:
  - app/ui/main_window.py
  - app/ui/db_connection_page.py
  - app/ui/file_select_page.py
acceptance_tests:
  - pytest
  - manual: python -m app.main
done_when:
  - old engine disposed before successful replacement
  - active engine disposed on MainWindow.closeEvent
  - file reselection clears mappings and validation
  - DB reconnection clears metadata/mappings/validation and replaces profile/engine/metadata
  - introspection failure disposes failed new engine and preserves previous known-good state
  - no credential-bearing URL is displayed or logged
```

Implementation notes:

- Prefer a small helper for engine disposal; because it is non-Qt behavior, place it where testable if practical, such as `app/core/db_connection.py`, or keep private in UI if minimal.
- On file reselection, preserve DB connection state but clear mapping-derived state.
- On DB replacement, preserve dataset but clear DB-derived and mapping-derived state.

### M1-T3: Worker lifecycle safety

```yaml
id: M1-T3
title: Validation/load worker lifecycle safety
change_type: code
depends_on: []
files:
  - app/ui/validation_page.py
  - app/ui/load_page.py
acceptance_tests:
  - pytest
  - manual: python -m app.main
done_when:
  - Validate button stored as instance attribute and disabled while running
  - Load/Dry Run buttons stored as instance attributes and disabled while running
  - repeated clicks while thread is running are ignored
  - status text shows running state
  - buttons re-enable on finished and failed
  - worker and thread deleteLater cleanup is wired
  - self.thread and self.worker reset after thread finish
```

Do not implement broad cancellation in this task. Existing `cancel()` methods are currently limited and should not be represented as full mid-flight cancellation.

### M1-T4: Loader transaction tests

```yaml
id: M1-T4
title: Loader transaction tests
change_type: test
files:
  - tests/test_loader.py
  - app/core/loader.py # only if small testability change is required
acceptance_tests:
  - pytest tests/test_loader.py
  - pytest
done_when:
  - dry-run counts rows without executing inserts
  - blocking validation errors raise ValueError before writes
  - insert success counts rows
  - insert failure rolls back all-or-nothing transaction
  - tests do not imply SQLite proves PostgreSQL-specific correctness
```

Test backend guidance:

- Use mocks/fakes for Python-side behavior.
- SQLite is acceptable only for generic SQLAlchemy transaction rollback if production code remains database-neutral.
- Add PostgreSQL integration coverage later for real PostgreSQL semantics.

## Implementation Milestone 2: Editable Column Mapping UI

### M2-T1: Pure core mapping helpers

```yaml
id: M2-T1
title: Pure core mapping helper contracts
change_type: code+test
depends_on: []
files:
  - app/core/mapping.py
  - tests/test_mapping.py
acceptance_tests:
  - pytest tests/test_mapping.py
done_when:
  - target_columns_for_mapping excludes identity/generated columns
  - source_options_for_sheet returns explicit source header options
  - update_column_mapping returns a new TableMapping and does not mutate input in place
  - required columns supplied by source mapping are tested
  - required columns supplied by constant_value mapping are tested
```

Required helper contract:

```python
def target_columns_for_mapping(table: TableDefinition) -> list[ColumnDefinition]:
    """Return columns displayed/mappable in the UI, excluding generated identity columns."""


def source_options_for_sheet(sheet: SourceSheet) -> list[str]:
    """Return source header options for UI selection."""


def update_column_mapping(
    mapping: TableMapping,
    target_column: str,
    source_column: str | None,
    transform: str | None = None,
    constant_value: object | None = None,
) -> TableMapping:
    """Return a new TableMapping with exactly one ColumnMapping for target_column."""
```

Rules:

1. Exclude `ColumnDefinition.is_identity` and `is_generated` from editable target rows by default.
2. Required columns are supplied when `source_column` is set or `transform == "constant_value"`.
3. Do not treat arbitrary constants as supplied unless transform semantics support them.
4. Preserve existing `required_columns()` behavior unless tests prove a safer adjustment is needed.

### M2-T2: Transform registry exposure

```yaml
id: M2-T2
title: Transform registry exposure and semantics
change_type: code+test
depends_on: []
files:
  - app/core/transforms.py
  - tests/test_transforms.py
acceptance_tests:
  - pytest tests/test_transforms.py
done_when:
  - UI_TRANSFORMS is exported from app.core.transforms
  - UI_TRANSFORMS includes constant_value
  - every UI_TRANSFORMS item except constant_value exists in TRANSFORMS
  - parse_json inclusion/exclusion policy is asserted
  - constant_value apply_transform behavior is tested
```

Implementation:

```python
UI_TRANSFORMS = [*TRANSFORMS.keys(), "constant_value"]
```

If `parse_json` is not appropriate for UI, create an explicit allowlist and include a comment/test explaining the exclusion.

### M2-T3: Editable ColumnMappingPage

```yaml
id: M2-T3
title: Editable ColumnMappingPage
change_type: code
depends_on:
  - M2-T1
  - M2-T2
files:
  - app/ui/column_mapping_page.py
acceptance_tests:
  - pytest
  - manual: python -m app.main
done_when:
  - one row rendered per mappable target column for each table mapping
  - source column uses QComboBox with empty option and source headers
  - transform uses QComboBox sourced from UI_TRANSFORMS
  - constant value is editable text
  - required/status columns reflect core mapping helpers
  - selecting constant_value ignores or disables source_column
  - user edit replaces mapping in state["mappings"]
  - user edit clears state["validation"]
  - refresh uses signal blocking and avoids recursive update loops
```

Target UI columns:

```text
Source sheet | Target column | Required | Source column | Transform | Constant value | Status
```

Implementation guardrails:

- Use `blockSignals(True)` or equivalent while populating widgets.
- Do not run validation from the widget.
- Avoid expensive full refresh work if inputs have not materially changed.
- Do not update UI from worker threads.

### M2-T4: Job persistence for edited mappings

```yaml
id: M2-T4
title: Edited mapping job persistence
change_type: test+code
depends_on:
  - M2-T1
files:
  - app/core/job_store.py
  - tests/test_job_store.py
acceptance_tests:
  - pytest tests/test_job_store.py
  - pytest
done_when:
  - ColumnMapping.source_column round-trips
  - ColumnMapping.target_column round-trips
  - ColumnMapping.transform round-trips
  - ColumnMapping.constant_value round-trips
  - older JSON missing optional fields still loads when applicable
  - profiles/jobs never persist database passwords
```

## Implementation Milestone 3: Validation Performance And Feedback

### M3-T1: Batched validation checks and unique-batch fix

```yaml
id: M3-T1
title: Batched validation checks and unique-batch fix
change_type: code+test
depends_on: []
files:
  - app/core/validation.py
  - tests/test_validation.py
acceptance_tests:
  - pytest tests/test_validation.py
  - pytest
done_when:
  - unique conflict DB checks are batched per constraint and chunk
  - FK DB checks are batched per FK and chunk
  - source row attribution is preserved
  - composite unique/FK behavior is preserved
  - keys with None values are skipped consistently
  - _validate_unique_batch applicability is based on mapped/supplied target columns, not rows[0]
  - query count scales by constraints × chunks, not row count
```

Batching constraints:

```yaml
batching:
  max_key_tuples_per_query: 500
  max_sql_parameters_per_query: 5000
  ordering: deterministic by first source row index
  query_count_goal: O(number_of_constraints * number_of_chunks)
```

Implementation notes:

- Keep `ValidationResult` shape unchanged.
- Keep existing `ValidationError.error_type` values (`unique_conflict`, `foreign_key`) unchanged.
- Do not log sensitive row values.

### M3-T2: Validation UI severity feedback

```yaml
id: M3-T2
title: Validation UI severity feedback
change_type: code
depends_on: []
files:
  - app/ui/validation_page.py
acceptance_tests:
  - pytest
  - manual: python -m app.main
done_when:
  - validation table includes Severity column
  - status text displays blocking/warning/total counts
  - error export fieldnames remain unchanged
```

Target UI columns:

```text
Severity | Sheet | Table | Row | Column | Type | Message
```

Target status text:

```text
Validation complete: <blocking_count> blocking, <warning_count> warning, <total_count> total.
```

## Implementation Milestone 4: Optional PostgreSQL Integration Tests

### M4-T1: PostgreSQL integration test harness

```yaml
id: M4-T1
title: PostgreSQL integration test harness
change_type: test
depends_on: []
files:
  - pyproject.toml
  - tests/integration/conftest.py
  - tests/integration/test_db_introspection_postgres.py
  - tests/integration/test_loader_postgres.py
acceptance_tests:
  - pytest
  - pytest -m integration # only when configured
done_when:
  - integration marker is registered
  - tests skip cleanly when env vars are absent
  - full PostgreSQL URLs/passwords are never printed or logged
  - introspection tests cover schema/table/view/enum/identity/generated/PK/unique/FK
  - loader tests cover insert success and rollback on failure
```

Environment options:

```text
ETL_TEST_POSTGRES_URL=postgresql+psycopg://user:password@host:port/database
```

Credential rules:

- Never print `ETL_TEST_POSTGRES_URL`.
- Never include password-bearing URLs in assertion messages.
- Redact URL strings in failure output.
- Prefer split env vars in CI:
  - `ETL_TEST_POSTGRES_HOST`
  - `ETL_TEST_POSTGRES_PORT`
  - `ETL_TEST_POSTGRES_DB`
  - `ETL_TEST_POSTGRES_USER`
  - `ETL_TEST_POSTGRES_PASSWORD`

## Implementation Milestone 5: Transaction Strategy Decision

### M5-T1: Transaction strategy documentation and compatibility

```yaml
id: M5-T1
title: Transaction strategy documentation and compatibility
change_type: docs+test
files:
  - README.md
  - MEMORY.md
  - app/core/loader.py
  - tests/test_loader.py
acceptance_tests:
  - pytest tests/test_loader.py
  - pytest
done_when:
  - all-or-nothing documented as only supported runtime behavior
  - EtlJob.transaction_strategy retained for saved-job compatibility
  - no UI implies per-table partial commits
  - tests assert all-or-nothing rollback
```

Decision:

- Do not implement `per_table` in this milestone.
- Implement only if users need partial commit semantics later.
- Do not add `transaction_strategy` parameter to `load_validated_rows()` unless needed now.

## Implementation Milestone 6: Large-File And Main-Thread Blocking Guardrails

### M6-T1: Large-file guardrails

```yaml
id: M6-T1
title: Large-file guardrails
change_type: code+test
depends_on: []
files:
  - app/core/file_loader.py
  - app/ui/file_select_page.py
acceptance_tests:
  - pytest
  - manual: python -m app.main
done_when:
  - file size warning threshold exists
  - users are warned before expensive full-file reads
  - preview reads stay bounded
  - small-file workflow remains unchanged
  - mappings/validation clear on new file selection
```

Recommended constant:

```python
LARGE_FILE_WARNING_BYTES = 100 * 1024 * 1024
```

Implementation notes:

- Warning is not a hard block.
- Consider `dtype=str` for CSV reads so validation owns type coercion.
- Consider `memory_map=True` for CSV where compatible.
- Do not redesign `ValidationResult` for streaming in this milestone.

### M6-T2: Future file and DB introspection workers

```yaml
id: M6-T2
title: Future file and DB introspection workers
change_type: future-code
depends_on:
  - M1-T3
files:
  - app/workers/file_load_worker.py
  - app/workers/db_introspection_worker.py
  - app/ui/file_select_page.py
  - app/ui/db_connection_page.py
done_when:
  - file loading no longer blocks GUI thread
  - DB connection/introspection no longer blocks GUI thread
  - state updates happen only in main-thread signal slots
```

This task is documented as a future risk-reduction item unless promoted into the current milestone.

## Implementation Milestone 7: Future Editable Table Mapping

### M7-T1: Editable TableMappingPage

```yaml
id: M7-T1
title: Future editable table mapping
change_type: future-code
depends_on:
  - M2-T1
files:
  - app/ui/table_mapping_page.py
  - app/core/mapping.py
done_when:
  - user can manually select target schema/table for a source sheet
  - user can add/remove table mappings
  - changing target table clears stale column mappings and validation for that mapping
  - manual choices flow into ColumnMappingPage and validation
```

## Cross-Cutting Test Matrix

| Area | Test file | Required command |
| --- | --- | --- |
| mapping helpers | `tests/test_mapping.py` | `pytest tests/test_mapping.py` |
| transforms registry | `tests/test_transforms.py` | `pytest tests/test_transforms.py` |
| job persistence | `tests/test_job_store.py` | `pytest tests/test_job_store.py` |
| validation behavior | `tests/test_validation.py` | `pytest tests/test_validation.py` |
| loader transactions | `tests/test_loader.py` | `pytest tests/test_loader.py` |
| full unit suite | `tests/` | `pytest` |
| UI smoke | manual | `python -m app.main` |
| PostgreSQL integration | `tests/integration/` | `pytest -m integration` |

## Manual Smoke Scenario

Use a disposable PostgreSQL database and a small CSV/XLSX file.

1. Launch app: `python -m app.main`.
2. File page:
   - select source file;
   - confirm preview and header warnings;
   - select a different source file and confirm old mapping/validation state is cleared.
3. Database page:
   - enter connection;
   - test and introspect;
   - confirm table count;
   - reconnect to a different DB/profile and confirm old metadata/mappings/validation are cleared.
4. Tables page:
   - confirm or choose target table mapping where supported.
5. Columns page:
   - change one auto-mapped source column;
   - clear one optional mapping;
   - set one transform;
   - set one constant value for a required/default-like field if schema supports it.
6. Validation page:
   - run validation;
   - confirm severity counts;
   - verify repeated clicks do not start duplicate workers;
   - export errors if errors exist.
7. Load page:
   - run dry run;
   - run insert only if validation has no blocking errors;
   - confirm row counts;
   - verify repeated clicks do not start duplicate workers.
8. Close app:
   - confirm no visible crash or worker warning.

## Acceptance Criteria

The next implementation milestone is complete when:

1. Users can complete the full CSV/XLSX to PostgreSQL workflow with manually corrected column mappings.
2. Validation and loading are tested for success, failure, and rollback paths.
3. File reselection clears stale mappings/validation.
4. Reconnecting or closing the app disposes obvious engine resources and does not keep stale mappings/validation.
5. Validation/load workers do not allow duplicate concurrent runs and clean up reliably.
6. Edited mappings, transforms, and constants persist through saved jobs.
7. All normal tests pass with `pytest`.
8. UI smoke test passes with `python -m app.main`.
9. Documentation accurately describes setup, tests, transaction strategy, packaging command, and manual smoke workflow.

## Non-Goals

Do not implement in the next milestone:

- Upsert/merge loading.
- Staging-table workflow.
- Multi-database support.
- Complex expression language for transforms.
- Full streaming/chunked validation architecture.
- Installer/signing/notarization.
- Broad refactor away from `MainWindow.state`.
- Per-table transaction commits.

## Risk Controls

1. Credential safety:
   - never serialize passwords;
   - never log connection URLs with passwords;
   - keep password storage in keyring only;
   - redact PostgreSQL integration URLs in test output.
2. Data safety:
   - all insert loads require no blocking validation errors;
   - insert loads remain transactionally safe;
   - dry runs never write.
3. Compatibility:
   - existing saved jobs/profiles continue loading;
   - dataclass fields are not removed or renamed;
   - `EtlJob.transaction_strategy` remains for compatibility even while only all-or-nothing is supported.
4. Maintainability:
   - pure mapping/validation logic remains in `app/core`;
   - UI widgets remain orchestration-only;
   - new behavior receives focused tests;
   - `to_jsonable()` should either be cleaned up in future maintenance or documented as intentionally retained.
