# ETL Loader Continuation Plan

## Objective

Advance the existing `etl-loader` MVP from a functional prototype into a safer, more usable, and more testable desktop ETL tool. Prioritize fixes that unlock reliable end-to-end use before adding large-file streaming, upserts, staging workflows, multi-database support, or release packaging automation.

## Current State Summary

The project already has the core architecture in place: PySide6 workflow pages, pandas CSV/XLSX loading, PostgreSQL connection/introspection, table/column auto-mapping, validation, dry-run/insert loading, saved profiles/jobs, worker-thread wrappers, pytest coverage for mapping/transforms/validation/job persistence, and PyInstaller packaging config.

Known continuation gaps from `MEMORY.md`, source inspection, and consolidated plan review:

- Column mapping UI is read-only; users cannot edit source-to-target mappings, transforms, or constants.
- Table mapping UI is also effectively read-only after auto-suggestion; users cannot manually map a sheet to a schema/table when auto-match fails.
- `transaction_strategy` exists on `EtlJob` but loader only implements all-or-nothing transactions.
- SQLAlchemy engines are kept in UI state without a clear dispose lifecycle.
- Selecting a new file does not currently clear stale mappings or validation.
- Full source loading uses pandas in-memory DataFrames and runs synchronously on the GUI thread.
- DB connection testing and introspection currently run synchronously on the GUI thread.
- Unique and foreign-key validation query the database row-by-row and will be slow on larger datasets.
- In-memory unique-batch validation should be hardened so constraint applicability is based on mapped target columns, not only the first transformed row.
- Test coverage is light for loader transactions, DB introspection, keyring/profile behavior, and QThread/UI workflow.
- README setup paths are stale (`etl_loader` vs current `etl`).
- Worker cleanup/cancellation and button disabled states are minimal; existing cancellation hooks are not effective during long validation execution.
- Transform UI semantics need to account for `constant_value` being a special `apply_transform()` case, not a member of `TRANSFORMS`.
- Integration test configuration must not print, log, or assert full PostgreSQL URLs containing passwords.

## Cross-Cutting Rules For Future Work

### State transition rules

The shared `MainWindow.state` dictionary remains the current cross-page contract, but state invalidation must be explicit:

| Event | Preserve | Clear or dispose |
| --- | --- | --- |
| New file selected | `profile`, `engine`, `metadata` | `mappings`, `validation` |
| New DB connection succeeds | `dataset` | dispose old `engine`; clear old `metadata`, `mappings`, `validation`; replace `profile`, `engine`, `metadata` |
| DB introspection fails after creating engine | previous known-good state | dispose failed new engine |
| Mapping edited | `dataset`, `profile`, `engine`, `metadata`, updated `mappings` | `validation` |
| App close | no user state requirement | dispose active `engine` |

### Qt/threading rules

- Workers must never read from or write to `MainWindow.state` directly.
- UI pages must pass only the specific inputs needed into workers at construction time.
- Workers must communicate progress, results, and failures only through Qt signals.
- Main-thread slots update `MainWindow.state` and refresh widgets.
- UI widgets must not be updated from worker threads.
- Buttons that start long-running work must be disabled immediately and re-enabled on both success and failure.

### Transform and constant-value rules

- `constant_value` is a special case handled by `apply_transform()`, not a key in `TRANSFORMS`.
- UI-selectable transforms should be derived as `list(TRANSFORMS.keys()) + ["constant_value"]` unless there is a deliberate allowlist.
- If a deliberate UI allowlist excludes `parse_json`, document why.
- If `transform == "constant_value"`, the source column is ignored and may be disabled/cleared in the UI.
- Constant values are raw UI strings until validation applies transform and target-type coercion.
- Empty constant values follow existing missing/null semantics during validation.

### Testing boundaries

- Normal `pytest` must remain fast and not require PostgreSQL.
- Unit tests may use fakes/mocks for Python-side logic.
- SQLite may only be used for generic SQLAlchemy transaction behavior and must not be treated as proof of PostgreSQL-specific correctness.
- PostgreSQL integration tests are required for introspection, enums, identity/generated columns, unique/FK behavior, and real insert/rollback behavior.
- Integration test setup must never print full connection URLs, passwords, source row values, or credentials.

## Recommended Next Steps

### Phase 1: Stabilize End-To-End MVP

1. Fix documentation and developer ergonomics.
   - Update README commands to match the current repository path.
   - Add a short manual smoke-test checklist for the six-page workflow.
   - Document all-or-nothing as the only currently supported runtime transaction strategy.
   - Keep `MEMORY.md` updated if behavior changes.

2. Add loader transaction tests.
   - Cover dry-run row counts without DB writes.
   - Cover blocking validation errors preventing load.
   - Cover insert success with multiple mapped tables where feasible.
   - Cover all-or-nothing rollback on insert failure.
   - Use fakes/mocks for Python-side checks and real PostgreSQL integration tests for PostgreSQL-specific behavior.

3. Harden state and engine lifecycle.
   - Dispose any existing engine before replacing it after a new connection succeeds.
   - Dispose the active engine when `MainWindow` closes.
   - Clear `metadata`, `mappings`, and `validation` when the DB profile/engine changes.
   - Clear `mappings` and `validation` when a new source file is selected.
   - Preserve previous known-good DB state if a new introspection attempt fails after engine creation.
   - Ensure no credentials or connection URLs are logged or shown in full.

4. Improve worker lifecycle safety.
   - Disable validation/load buttons while a worker is running.
   - Re-enable buttons on finish/failure.
   - Connect worker/thread cleanup with `deleteLater()`.
   - Prevent duplicate concurrent validation/load runs.
   - Clearly document that current cancellation hooks do not interrupt validation once `validate_job()` is running.

5. Acknowledge main-thread blocking risks.
   - File loading and DB introspection currently block the GUI thread.
   - If not fixed in Phase 1, record them as known deferred risks with clear user-facing status/warning behavior.
   - Prefer future file-loading and introspection workers over making the GUI tolerate blocking calls.

Acceptance checks:

- `pytest` passes.
- Manual launch via `python -m app.main` works.
- Selecting a new file clears stale mapping/validation state.
- Reconnecting to a different database does not leave stale mappings/validation in state.
- Failed inserts still roll back and show a credential-safe message.
- Repeated validation/load clicks do not start duplicate workers.

### Phase 2: Make Column Mapping Actually Editable

1. Add pure core mapping helpers.
   - Helpers should return new `TableMapping` values rather than ambiguously mutating in place.
   - Exclude identity/generated columns from editable target rows by default.
   - Surface required-column status through core helpers rather than duplicating rules in widgets.

2. Convert column mapping display into an editable workflow.
   - Allow selecting or clearing the source column per target column.
   - Allow selecting supported transforms from the core transform registry plus `constant_value`.
   - Allow entering a constant value when constant transform is selected.
   - If `constant_value` is selected, ignore or disable source-column selection.
   - Preserve auto-mapping as the starting point rather than the final state.
   - Block widget signals while programmatically populating table rows to avoid recursive refresh loops.

3. Validate mapping completeness before validation runs.
   - Surface required target columns missing mappings directly on the Columns page.
   - Keep source columns optional unless mapped.
   - Clear stale `validation` whenever mappings change.

4. Persist edited mappings in saved jobs.
   - Confirm `ColumnMapping.transform` and `constant_value` round-trip correctly.
   - Add or update job-store tests for edited mappings and constants.

Acceptance checks:

- A user can correct an incorrect auto-map without editing JSON.
- A user can set a constant/default-like value through the UI.
- Validation uses edited mappings exactly as displayed.
- Job save/load preserves manual mapping choices.
- Transform UI includes or deliberately excludes `parse_json` with documented reasoning.

### Phase 3: Improve Validation Performance And Feedback

1. Batch database uniqueness checks.
   - Replace row-by-row unique conflict queries with grouped/batched lookups per unique constraint.
   - Keep source row attribution for reported errors.
   - Add chunking limits so SQL parameter count stays bounded.

2. Batch foreign-key checks.
   - Query distinct FK key tuples once per FK constraint per chunk.
   - Report missing references against the relevant source rows.
   - Preserve composite FK behavior.

3. Fix in-memory unique-batch applicability.
   - Determine whether a unique constraint can be checked from mapped/supplied target columns, not from only `rows[0]`.
   - Preserve behavior for constraints with nullable values by skipping keys containing `None`.

4. Improve validation output.
   - Include severity in the UI table.
   - Show blocking/warning/total counts in status text.
   - Consider showing transformed value in details/export only, not necessarily in the main table.

5. Expand validation tests.
   - Unique duplicates within source.
   - Unique conflicts against target.
   - Foreign-key missing rows.
   - Enum, JSON, numeric precision/scale, and nullability edge cases.

Acceptance checks:

- Validation DB query count scales by constraints × chunks, not source row count.
- Batch size and SQL parameter limits are documented and tested.
- Error exports remain compatible and credential-safe.
- Existing validation behavior remains unchanged except for performance, bug fixes, and clearer reporting.

### Phase 4: Add PostgreSQL Integration Coverage

1. Add optional PostgreSQL integration tests.
   - Mark them separately, for example `pytest -m integration`.
   - Use environment variables for connection details.
   - Prefer split env vars in CI; a URL env var is acceptable only if never printed or logged.
   - Skip cleanly when no test database is configured.

2. Cover introspection realistically.
   - Schemas, tables, views.
   - Identity/generated columns.
   - Enums.
   - Primary keys, unique constraints, and foreign keys.

3. Cover end-to-end database behavior.
   - Insert success.
   - All-or-nothing rollback on failure.
   - Unique/FK validation against real PostgreSQL.

Acceptance checks:

- Normal `pytest` remains fast and does not require PostgreSQL.
- Integration tests can be run explicitly against a disposable PostgreSQL database.
- Test setup never stores, prints, or logs credentials.

### Phase 5: Clarify Transaction Strategy

1. Defer `per_table` unless product need is clear.
   - Keep `EtlJob.transaction_strategy` for saved-job compatibility.
   - Document all-or-nothing as the only supported runtime behavior.
   - Hide or avoid any UI affordance that implies per-table partial commits.

2. Preserve default safety.
   - Keep all-or-nothing as the default.
   - Keep blocking validation errors as a hard load stop.
   - Ensure cancellation or insert failure rolls back the active transaction.

3. Add tests for the chosen behavior.
   - All-or-nothing rollback.
   - Saved job compatibility for existing `transaction_strategy` values.

Recommended choice:

- Implement `per_table` only if users explicitly need partial commit semantics. Otherwise defer it and keep the loader simpler.

### Phase 6: Address Large-File And Main-Thread Blocking Risk Incrementally

1. Add file-size and row-count guardrails.
   - Warn users before fully loading very large CSV/XLSX files.
   - Show clear estimated memory-risk messaging.

2. Reduce eager pandas costs where safe.
   - Keep previews limited.
   - Consider `dtype=str` for CSV reads so validation owns type coercion.
   - Consider `memory_map=True` for CSV where compatible.

3. Move blocking file and DB metadata operations to workers in a future iteration.
   - File loading worker for full source reads.
   - DB introspection worker for slow/large schemas.
   - Keep worker results returned by signals and state updates on the main thread.

4. Add streaming/chunked CSV path later.
   - Start with CSV chunk validation because XLSX streaming is more constrained.
   - Keep transformed-row storage semantics in mind before changing `ValidationResult`.
   - Avoid redesigning around streaming until the MVP is stable and tested.

Acceptance checks:

- Users get a clear warning before expensive full-file reads.
- Existing small-file workflow remains unchanged.
- Long-running future file/introspection work does not update UI from worker threads.
- Any streaming change preserves validation and load safety semantics.

### Phase 7: Editable Table Mapping

1. Add manual table mapping controls.
   - Allow selecting target schema/table when auto-suggestion fails or is wrong.
   - Allow adding/removing mappings.
   - Preserve manual table choices before column mapping.

2. Recompute column suggestions when a table target changes.
   - Clear stale column mappings/validation for the changed table mapping.
   - Keep source sheet and selected target table as the table-level contract.

Acceptance checks:

- A user can map a source sheet manually to any introspected target table.
- Manual table choices are reflected in column mapping and validation.

### Phase 8: Packaging And Release Readiness

1. Verify PyInstaller spec after dependency/import changes.
   - Keep hidden imports for `psycopg` and `keyring.backends` current.
   - Run native builds on each target OS when release work begins.

2. Add basic CI.
   - Run unit tests on supported Python versions.
   - Optionally add lint/type checks only after choosing tools.
   - Keep integration tests opt-in unless CI provisions PostgreSQL.

3. Create a release checklist.
   - Clean-machine launch.
   - CSV/XLSX parsing.
   - PostgreSQL connection.
   - Keyring profile save/load.
   - Validation, dry-run, insert, rollback.

Acceptance checks:

- Unit tests run automatically in CI.
- Packaging verification is documented and repeatable.
- Release artifacts are tested on their native OS.

## Implementation Order

Recommended order for the next development sessions:

1. Phase 1: stabilize MVP, state/engine lifecycle, worker cleanup, loader tests, README correction.
2. Phase 2: editable column mappings and persisted edited jobs.
3. Phase 3: batched validation checks, in-memory uniqueness fix, and better validation feedback.
4. Phase 4: PostgreSQL integration tests.
5. Phase 5: transaction strategy documentation/deferral.
6. Phase 6: large-file guardrails and deferred workerization for file/introspection operations.
7. Phase 7: editable table mappings.
8. Phase 8: CI and packaging release work.

## Testing Strategy

Run `pytest` after core ETL, validation, mapping, loader, transform, or persistence changes. For UI-only changes, also run a manual `python -m app.main` smoke test. For DB-specific behavior, add opt-in PostgreSQL integration tests that skip when credentials are not configured and redact connection details from output.

## Non-Goals For The Next Iteration

- Upsert/merge loading.
- Staging-table workflows.
- Multi-database support.
- Complex transformation expressions.
- Full streaming architecture rewrite.
- Installer/signing/notarization work before core workflow stabilization.
- Broad refactor away from `MainWindow.state`.

## Definition Of Done For The Next Milestone

- Users can complete the full CSV/XLSX to PostgreSQL workflow with manually corrected column mappings.
- Validation and loading are tested for success, failure, and rollback paths.
- File reselection, mapping edits, reconnecting, and closing the app do not leave stale state or obvious engine resource leaks.
- Validation/load workers clean up reliably and do not allow duplicate concurrent runs.
- Documentation accurately reflects local setup, test strategy, transaction strategy, and smoke-test steps.
