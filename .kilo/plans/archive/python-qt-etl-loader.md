# Python Qt ETL Loader Plan

## Objective
Build a standalone cross-platform Python desktop application for ETL loading CSV/XLSX files into PostgreSQL. The app must let users select a file, connect to PostgreSQL, map source sheets/files to target tables, map source headers to target columns, validate data against database metadata before loading, and bulk insert data safely.

## Scope

### MVP
- PySide6 desktop GUI.
- Load one CSV or XLSX file per ETL job.
- XLSX: support multiple sheets.
- CSV: support one logical source table.
- PostgreSQL target support first.
- Database introspection for schemas, tables, columns, data types, nullability, defaults, primary keys, unique constraints, foreign keys, and enums where available.
- Manual table mapping with basic auto-suggestions.
- Manual column mapping with basic auto-mapping.
- Basic transformations: trim strings, empty string to NULL, date parsing, boolean normalization, numeric parsing, constant/default values.
- Validation before load.
- Dry run.
- Transactional batch insert.
- Validation error export.
- Load summary report.
- Saved ETL job definitions.
- Saved DB connection profiles with passwords stored via OS keychain.
- Cross-platform packaging for Windows, macOS, and Linux.

### Deferred
- Upsert/merge loading.
- Staging table workflow.
- Inline source data editing.
- Complex transformation expressions.
- Multi-database support beyond PostgreSQL.
- Scheduling/background automation.
- Cloud file sources.
- Multi-user/shared mapping repository.
- Full automated foreign-key load ordering if not needed for MVP.

## Recommended Stack
- GUI: `PySide6`.
- Data loading: `pandas`, `openpyxl`.
- PostgreSQL: `SQLAlchemy` for introspection/metadata, `psycopg[binary]` for loading.
- Config paths: `platformdirs`.
- Secret storage: `keyring`.
- Testing: `pytest`.
- Packaging: `PyInstaller`; later platform installers via Inno Setup, DMG tooling, AppImage.

## Proposed Project Layout
```text
etl_loader/
├── app/
│   ├── main.py
│   ├── ui/
│   │   ├── main_window.py
│   │   ├── file_select_page.py
│   │   ├── db_connection_page.py
│   │   ├── table_mapping_page.py
│   │   ├── column_mapping_page.py
│   │   ├── validation_page.py
│   │   └── load_page.py
│   ├── core/
│   │   ├── file_loader.py
│   │   ├── db_connection.py
│   │   ├── db_introspection.py
│   │   ├── mapping.py
│   │   ├── transforms.py
│   │   ├── validation.py
│   │   ├── loader.py
│   │   ├── job_store.py
│   │   └── models.py
│   ├── workers/
│   │   ├── validation_worker.py
│   │   └── load_worker.py
│   └── config/
│       └── settings.py
├── tests/
├── packaging/
│   ├── pyinstaller/
│   └── installers/
├── pyproject.toml
└── README.md
```

## Core Workflow
1. User creates or opens an ETL job.
2. User selects CSV/XLSX source file.
3. App reads file metadata and previews data.
4. User connects to PostgreSQL or selects saved connection profile.
5. App introspects target database metadata.
6. User maps sheets/files to database tables.
7. User maps source headers to target columns.
8. User selects basic transforms/defaults where needed.
9. App validates source rows against target metadata.
10. User reviews validation errors and exports report if needed.
11. User runs dry run or load.
12. App inserts rows transactionally and reports success/failure.

## UI State Rules
- File preview disabled until a file is selected and parsed.
- Database table browser disabled until connection test succeeds.
- Table mapping disabled until both source metadata and DB metadata are available.
- Column mapping disabled until at least one table mapping exists.
- Validation disabled until required mappings are complete.
- Load button disabled until validation passes or user explicitly chooses an allowed non-blocking warning mode.
- Long-running validation/load operations run in Qt worker threads with progress and cancellation.

## Data Models
```python
@dataclass
class SourceDataset:
    file_path: str
    file_type: Literal["csv", "xlsx"]
    sheets: dict[str, pd.DataFrame]

@dataclass
class ConnectionProfile:
    name: str
    host: str
    port: int
    database: str
    username: str
    ssl_mode: str | None
    default_schema: str | None

@dataclass
class ColumnDefinition:
    schema: str
    table: str
    name: str
    data_type: str
    nullable: bool
    has_default: bool
    max_length: int | None
    numeric_precision: int | None
    numeric_scale: int | None
    enum_values: list[str] | None
    is_primary_key: bool
    is_identity: bool

@dataclass
class ColumnMapping:
    source_column: str | None
    target_column: str
    transform: str | None = None
    constant_value: object | None = None

@dataclass
class TableMapping:
    source_sheet: str
    target_schema: str
    target_table: str
    column_mappings: list[ColumnMapping]

@dataclass
class EtlJob:
    name: str
    source_file_path: str
    connection_profile_name: str
    table_mappings: list[TableMapping]
    transaction_strategy: Literal["all_or_nothing", "per_table"]
    load_mode: Literal["dry_run", "insert_only"]
```

## File Loading Plan
- CSV:
  - Detect delimiter where possible; allow manual override.
  - Support encoding selection; default UTF-8.
  - Treat as one source sheet named after file stem.
- XLSX:
  - Use `openpyxl` via pandas.
  - Load sheet names first.
  - Load preview rows before full dataset where feasible.
  - Preserve original headers but also compute normalized headers for auto-mapping.
- Header handling:
  - Detect duplicate headers and block mapping until resolved.
  - Detect empty headers and assign temporary display names, but require explicit mapping.

## PostgreSQL Introspection Plan
Collect:
- Schemas.
- Tables/views, with views optionally read-only/deferred for MVP.
- Columns and PostgreSQL type metadata.
- Nullability/defaults/identity/generated columns.
- Primary keys.
- Unique constraints.
- Foreign keys.
- Enum allowed values.

Use SQLAlchemy inspector where sufficient; supplement with PostgreSQL catalog queries for enums, identity/generated columns, precision/scale, and more accurate type details.

## Mapping Plan
- Table auto-suggestions:
  - Exact sheet/table name match.
  - Case-insensitive match.
  - Snake-case/space-insensitive match.
- Column auto-mapping:
  - Exact match.
  - Case-insensitive match.
  - Normalized match: trim, lower, replace spaces/hyphens with underscores, collapse punctuation.
- Required target columns:
  - Required if not nullable, no default, not identity/generated, and not otherwise supplied by constant/default mapping.
- Allow unmapped source columns.
- Block validation when required target columns are unmapped.

## Transform Plan
MVP transforms:
- `trim_string`.
- `empty_to_null`.
- `parse_date`.
- `parse_timestamp`.
- `parse_boolean` accepting true/false, yes/no, y/n, 1/0.
- `parse_integer`.
- `parse_decimal`.
- `parse_uuid`.
- `constant_value`.

Apply transforms before validation and before loading. Validation reports transformed value where useful while preserving original source value in error details.

## Validation Plan
Validation should be row-level and table-level before insert.

Blocking validations:
- Required target column missing.
- Non-null target receives null/empty after transform.
- Integer/bigint parse failure.
- Numeric/decimal parse failure.
- Numeric precision/scale overflow where metadata is available.
- Boolean parse failure.
- Date/timestamp parse failure.
- UUID parse failure.
- JSON/JSONB parse failure.
- Enum value not in allowed values.
- String exceeds target `varchar(n)`/`char(n)` length.
- Duplicate source headers.

Recommended validations:
- Unique constraint duplicates within source batch.
- Unique constraint conflicts against target table.
- Foreign key existence against target DB for mapped FK columns.

Validation output columns:
- Source sheet.
- Target schema/table.
- Row number.
- Source column.
- Target column.
- Original value.
- Transformed value.
- Error type.
- Message.
- Severity: blocking/warning.

## Load Plan
MVP loading mode:
- `insert_only` using parameterized batch inserts.
- Default transaction strategy: all-or-nothing.
- Optional per-table transaction strategy after MVP if needed.
- Exclude identity/generated columns unless explicitly supported by DB/table.
- Insert transformed/validated values only.
- Roll back on failure.
- Show inserted row counts per table and total elapsed time.

Future loading modes:
- COPY-based load for large datasets.
- Upsert by selected key.
- Truncate-and-reload.
- Staging-table validation and merge.

## Error Handling
Define explicit behavior for:
- File open/parse failure: show message and keep previous valid state only if safe.
- Malformed CSV rows: show parse error with file line when available.
- Duplicate/empty headers: block mapping until corrected or manually resolved.
- DB connection failure: show connection diagnostics without logging password.
- Validation failure: block load; allow error export.
- Insert failure: rollback active transaction; show failed table and DB error.
- User cancellation: cancel worker; rollback if load was active.
- App crash/restart: persisted jobs remain; in-flight loads are not resumed in MVP.

## Config, Secrets, Logs
- Store connection profiles and ETL jobs under `platformdirs.user_config_dir()`.
- Store DB passwords with `keyring`; JSON profiles contain keyring reference only.
- Store logs under `platformdirs.user_log_dir()`.
- Never log passwords or full connection URLs containing passwords.
- Log lifecycle events: file loaded, DB connected, mappings saved, validation started/completed, load started/completed, rows inserted, rollback/failure.

## Testing Plan
Unit tests:
- CSV loading.
- XLSX loading.
- Header normalization.
- Table auto-matching.
- Column auto-matching.
- Transform functions.
- Type validation.
- Nullability validation.
- Length validation.
- ETL job serialization.

Integration tests:
- PostgreSQL connection and introspection.
- Enum introspection.
- Insert success.
- Rollback on insert failure.
- Unique conflict detection.
- Foreign key validation where implemented.

GUI smoke tests:
- App starts.
- Main window loads.
- Page navigation works.
- Worker progress signals do not freeze UI.

Use a Docker PostgreSQL container for integration tests.

## Cross-Platform Packaging Plan
- Use PyInstaller as the primary packager.
- Build native artifacts on each target OS; do not rely on one OS building all platforms.
- Windows:
  - Build `.exe`/one-folder artifact with PyInstaller.
  - Later package with Inno Setup or NSIS.
  - Code signing recommended to reduce SmartScreen friction.
- macOS:
  - Build `.app` bundle with PyInstaller.
  - Later create `.dmg`.
  - Signing and notarization required for smooth public distribution.
  - Build/test separately for Apple Silicon and Intel if universal build is not configured.
- Linux:
  - Start with one-folder or AppImage.
  - Later add `.deb` if needed.
- CI release matrix:
  - `windows-latest`.
  - `macos-latest`.
  - `ubuntu-latest`.
- Packaging verification:
  - Launch on clean machine/VM.
  - Verify Qt libraries load.
  - Verify XLSX/CSV parsing.
  - Verify PostgreSQL connection without local dev dependencies.
  - Verify keyring and config paths work.

## Implementation Phases

### Phase 1: Project Foundation
- Create Python project with dependency management.
- Add PySide6 app shell and main window.
- Add basic navigation between workflow pages.
- Add logging/config path setup.

### Phase 2: File Loading
- Implement CSV/XLSX source loading.
- Add sheet/source list and preview table.
- Add duplicate/empty header detection.

### Phase 3: PostgreSQL Connection and Introspection
- Implement connection form and test connection.
- Add connection profile persistence.
- Store password via keyring.
- Introspect schemas/tables/columns/constraints/enums.
- Display database metadata in UI.

### Phase 4: Mapping
- Implement sheet-to-table mapping.
- Implement source-header-to-target-column mapping.
- Add auto-map suggestions.
- Add saved ETL job JSON.

### Phase 5: Transforms and Validation
- Implement MVP transform functions.
- Implement validation engine.
- Add validation worker thread.
- Add validation result table and CSV export.

### Phase 6: Loading
- Implement dry run.
- Implement transactional batch insert.
- Add load worker thread with progress/cancel.
- Add rollback handling and load summary report.

### Phase 7: Tests
- Add unit tests for core non-GUI logic.
- Add PostgreSQL integration tests.
- Add GUI smoke tests.

### Phase 8: Packaging and Release
- Add PyInstaller spec/config.
- Add platform-specific build scripts.
- Add CI build matrix.
- Add clean-machine packaging verification checklist.
- Add installers/signing/notarization later as release maturity increases.

## Key Risks and Mitigations
- Messy spreadsheet data: normalize and validate before DB writes; preserve original values in reports.
- Large files: pandas is acceptable for MVP; consider streaming/COPY later.
- PostgreSQL type edge cases: supplement SQLAlchemy with catalog queries.
- Bulk insert error localization: strong pre-validation and transactional rollback.
- Foreign key dependency order: allow manual table load order initially; add FK graph later.
- Packaging Qt and database drivers: test each OS artifact on clean systems early.
- Credential leakage: keyring storage and log redaction from the start.

## Acceptance Criteria
- User can import CSV/XLSX, preview source data, connect to PostgreSQL, map source to target, validate rows, and insert data into PostgreSQL.
- App blocks unsafe loads when validation has blocking errors.
- Failed loads rollback transactionally.
- Validation errors can be exported.
- Successful load produces row-count summary.
- Saved jobs and connection profiles can be reused.
- App packages and launches on Windows, macOS, and Linux from native builds.
