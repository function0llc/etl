# MEMORY

## Project Overview

Standalone Python/PySide6 desktop ETL loader for CSV/XLSX -> PostgreSQL. Workflow: load source file, connect/introspect DB, auto-map sheets/columns, validate transformed rows, dry-run or insert transactionally. Early but functional app; core tests exist for mapping/transforms/validation/job persistence.

## Tech Stack

Python >=3.11; PySide6 GUI; pandas/openpyxl file ingestion; SQLAlchemy 2 + psycopg3 PostgreSQL access; platformdirs config/log paths; keyring password storage; pytest; PyInstaller packaging.

## Architecture Overview

`app/main.py` calls `setup_logging()`, creates `QApplication`, instantiates `MainWindow`, then enters Qt event loop.

`MainWindow` builds pages for File, Database, Tables, Columns, Validation, Load. It passes one mutable `state: dict` plus a refresh callback to each page.

UI pages in `app/ui` orchestrate user actions and shared state. Core ETL behavior is in `app/core`. Blocking validation/load work is wrapped by `app/workers` and executed on `QThread`.

Data flow: source file -> `SourceDataset`; DB connection -> SQLAlchemy `Engine` + `DatabaseMetadata`; mapping suggestions -> `TableMapping`; validation -> `ValidationResult`; load -> `LoadSummary`.

## Directory Map

`app/config/settings.py`: APP_NAME/APP_AUTHOR, platformdirs config/log dirs, logging setup.

`app/core/models.py`: dataclass contracts used across UI/core/persistence.

`app/core/file_loader.py`: CSV/XLSX load, dialect sniffing, sheet/header metadata.

`app/core/db_connection.py`: PostgreSQL URL/engine, connection test, keyring password save/get.

`app/core/db_introspection.py`: schemas, tables/views, columns, PKs, uniques, FKs, enum/identity/generated metadata.

`app/core/mapping.py`: normalized name matching, mapping suggestions, required-column checks.

`app/core/transforms.py`: transform registry and coercion helpers.

`app/core/validation.py`: required mapping, type/nullability/enum/length/numeric, unique, FK validation; CSV error export.

`app/core/loader.py`: dry-run counts and transactional inserts.

`app/core/job_store.py`: profile/job JSON persistence under user config dir.

`app/ui/*_page.py`: PySide pages for workflow steps.

`app/workers/*`: QObject workers for validation/load threads.

`tests/`: pytest coverage for mapping, transforms, validation, loader transactions, and job store.

`packaging/pyinstaller/etl-loader.spec`: PyInstaller app bundle spec.

## Dependency Graph

`app.main` -> `settings`, `MainWindow`.

`MainWindow` -> UI pages -> `app/core` modules + workers.

`workers` -> `validation.validate_job` / `loader.load_validated_rows`.

`validation` -> `mapping.required_columns`, `models`, `transforms`, SQLAlchemy selects.

`loader` -> SQLAlchemy reflection/insert, `ValidationResult`.

`job_store` -> `settings.config_dir`, model dataclasses.

No known circular imports in current source.

## Data Model Overview

Core dataclasses: `SourceSheet`, `SourceDataset`, `ConnectionProfile`, `ColumnDefinition`, `UniqueConstraint`, `ForeignKey`, `TableDefinition`, `DatabaseMetadata`, `ColumnMapping`, `TableMapping`, `EtlJob`, `ValidationError`, `ValidationResult`, `LoadSummary`.

Saved profiles are JSON metadata plus `password_key`; passwords are externalized to keyring. Saved jobs serialize mappings and source/profile names. `to_jsonable()` exists but current `job_store` primarily uses `asdict()`.

## API And Integration Summary

No HTTP API. External integrations: local filesystem, PostgreSQL, OS keyring, platform-specific config/log directories. DB introspection uses SQLAlchemy inspector plus direct PostgreSQL catalog queries for enums and identity/generated columns.

## State Management

Single mutable `MainWindow.state` dict stores `dataset`, `profile`, `engine`, `metadata`, `mappings`, `validation`. Pages refresh from this dict. No reactive store beyond Qt signals/callbacks.

## Auth & Security

No app-level auth. PostgreSQL credentials entered in UI. `keyring` service name is `etl-loader-postgres`; `password_key` format is `profile:username@host/database`. Do not serialize or log passwords/URLs/source row data.

## Build / Run / Deploy

Install: `python -m venv .venv`; `source .venv/bin/activate`; `python -m pip install -e '.[dev]'`.

Run: `python -m app.main` or console script `etl-loader` after install.

Test: `pytest`.

Package: `pyinstaller packaging/pyinstaller/etl-loader.spec`; verify artifacts per target OS.

No CI/CD or deployment config found.

## Development Conventions

Python modules use `from __future__ import annotations` and dataclasses. Keep core logic pure/testable; keep PySide code in UI; thread blocking work via workers. Error handling is mostly user-facing strings in UI and typed/core exceptions in transforms/load. Logging configured globally to file + stream.

## Critical Engineering Knowledge

`MainWindow.closeEvent` now disposes the active SQLAlchemy `Engine`; `DbConnectionPage` also disposes the previous engine when replacing a connection and disposes failed new engines on introspection failure.

`load_source_file_full()` loads full source files into memory; large files are a scalability risk.

Validation unique/FK checks query row-by-row and can be slow on large batches.

`ColumnMappingPage` now renders editable per-target-column rows with source selection, transform selection (including `constant_value`), constant input, and required/status feedback; mapping edits clear stale validation state.

Load path uses one `engine.begin()` transaction for all mapped tables; failure/cancel raises and should roll back.

`transaction_strategy` exists on `EtlJob` but loader currently uses one transaction path; per-table strategy is not implemented in observed code.

`README.md` says `cd etl_loader`; current directory name is `etl`.

## Dead Code & Cleanup Candidates

Medium confidence: `EtlJob.transaction_strategy` is unused by loader.

Medium confidence: `to_jsonable()` is unused in current persistence path.

High confidence: prior generic `AGENTS.md` had stale/non-project-specific content and a stray `s`; rewritten.

Coverage gaps: DB introspection, keyring/profile edge cases beyond basic persistence, and full QThread/UI workflows.

## Safe Modification Guide

High-risk files: `app/core/validation.py`, `app/core/loader.py`, `app/core/db_introspection.py`, `app/core/db_connection.py`, `app/core/models.py`.

When changing validation/load, preserve `ValidationResult` shape, blocking error semantics, dry-run no-insert behavior, and transactional insert rollback. Add focused tests.

When changing models/job persistence, consider saved JSON compatibility and password separation.

When changing DB connection/introspection, avoid logging secrets and test against realistic PostgreSQL schema features.

When changing dependencies/imports, review PyInstaller hidden imports.

## Current Work / Open Problems

Project-specific `AGENTS.md` and this `MEMORY.md` were added to replace generic AI instructions. Open engineering concerns: large-file memory use, row-by-row DB validation performance, synchronous file load/DB introspection on the UI thread, and unimplemented per-table transaction strategy.

## AI Session Continuation Notes

Read first: `MEMORY.md`, `AGENTS.md`, `pyproject.toml`, `app/core/models.py`, then the module being changed. Keep domain logic in `app/core`; use UI only for orchestration. Always protect credentials. Run `pytest` for core changes. Check PyInstaller spec after dependency/runtime import changes.
