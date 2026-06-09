# Project AI Instructions

Always read `MEMORY.md` before analysis, planning, refactoring, implementation, or code review. Follow the architecture, risks, and conventions recorded there. If `MEMORY.md` is missing or stale, create/update it as part of the work and keep it concise.

## Project Identity

This repo is `etl-loader`: a Python 3.11+ standalone PySide6 desktop app for loading CSV/XLSX data into PostgreSQL. It has no web frontend/backend split. The GUI orchestrates a local ETL workflow, while domain logic lives in testable core modules.

Primary workflow: select source file -> connect/introspect PostgreSQL -> suggest table/column mappings -> validate rows -> dry-run or insert rows transactionally.

## Commands

Use only commands that match the current project tooling.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m app.main
pytest
pyinstaller packaging/pyinstaller/etl-loader.spec
```

Run `pytest` after changing core ETL, validation, mapping, persistence, or transform logic. UI-only changes may need a manual `python -m app.main` smoke test. Packaging/dependency changes require checking the PyInstaller spec.

## Architecture Rules

Keep ETL/business logic in `app/core` and make it independently testable. Do not embed validation, transformation, database loading, or persistence rules inside PySide widgets when a core function is appropriate.

Keep PySide6 UI code in `app/ui`. UI pages should orchestrate shared state, user interaction, and calls into core modules. `MainWindow.state` is currently the cross-page mutable state contract.

Keep long-running GUI work in `app/workers` using `QObject`, `QThread`, and Qt signals. Avoid blocking the UI thread with file parsing, database validation, or inserts.

Use dataclasses in `app/core/models.py` as cross-module contracts. Preserve their fields unless all callers, serializers, tests, and saved-job compatibility are considered.

## Module Boundaries

`app/main.py` bootstraps logging, `QApplication`, and `MainWindow`.

`app/config/settings.py` owns platformdirs-backed config/log paths and logging setup.

`app/core/file_loader.py` owns CSV/XLSX loading, dialect sniffing, sheet metadata, and header warnings.

`app/core/db_connection.py` owns PostgreSQL URLs, SQLAlchemy engines, connection tests, and keyring password storage.

`app/core/db_introspection.py` owns schema/table/column/constraint introspection.

`app/core/mapping.py` owns table/column mapping suggestions and required-column checks.

`app/core/transforms.py` owns transform functions and missing/null coercion semantics.

`app/core/validation.py` owns row validation, type coercion, uniqueness checks, foreign-key checks, and validation error export.

`app/core/loader.py` owns dry-run summaries and transactional inserts.

`app/core/job_store.py` owns profile/job JSON persistence in the user config directory.

`app/workers/*` bridge blocking core work to Qt threads/signals.

## Security And Persistence

Never persist database passwords in JSON profiles, jobs, logs, tests, fixtures, screenshots, or error messages. Passwords belong in `keyring` via `app/core/db_connection.py`; profile JSON stores metadata and a password key only.

Do not log connection URLs, credentials, source file contents, or sensitive row values. Keep connection failure messages diagnostic but credential-safe.

Profiles and jobs live under `platformdirs.user_config_dir(APP_NAME, APP_AUTHOR)`. Logs live under `platformdirs.user_log_dir(...)`. Preserve saved-job/profile compatibility when changing serialized dataclasses.

## Validation And Loading Rules

Insert loads must remain blocked when `ValidationResult.has_blocking_errors` is true.

Dry-run mode must count transformed rows without inserting anything.

Insert mode must preserve transactional behavior through `engine.begin()`. Cancellation or insert failure should roll back the active transaction.

Be careful with PostgreSQL schema/table names, identity/generated columns, defaults, nullable columns, enums, numeric precision/scale, unique constraints, and foreign keys.

Row-by-row uniqueness/FK database checks can be expensive on large datasets; optimize carefully and cover behavior with tests.

## Testing Expectations

Add or update tests in `tests/` for changes to mapping, transforms, validation, loader behavior, and job/profile serialization.

Prefer focused core tests over GUI tests when behavior can be tested outside PySide. For UI changes, keep core behavior unchanged unless the requested work requires otherwise.

Existing tests cover mapping, transforms, validation, and job store round-trips; loader transactions, DB introspection, keyring behavior, and full UI flows are not currently well covered.

## Packaging

The PyInstaller spec is `packaging/pyinstaller/etl-loader.spec`. It currently collects hidden imports for `psycopg` and `keyring.backends`. Update it if import paths, runtime dependencies, or packaging-sensitive modules change.

Build and verify artifacts on each target OS instead of assuming cross-compilation works.

## Development Conventions

Use Python 3.11+ typing and the existing `from __future__ import annotations` pattern.

Prefer small, pure functions in `app/core`; keep side effects at boundaries such as files, keyring, database engines, Qt widgets, and logging.

Keep comments rare and operational. Do not add broad tutorials or generic framework explanations.

Preserve existing user data semantics unless a migration/update path is included. Avoid broad refactors when a smaller correct change solves the task.

Update `MEMORY.md` whenever significant architecture, workflow, dependency, persistence, validation, loading, or packaging behavior changes. Replace stale facts instead of appending endlessly.
