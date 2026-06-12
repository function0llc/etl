# ETL Loader

Standalone PySide6 desktop app for loading CSV/XLSX data into PostgreSQL with schema introspection, mapping, validation, dry runs, transactional inserts, saved jobs, keyring-backed connection profiles, and PyInstaller packaging.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m app.main
pytest
```

## Manual Smoke Checklist

1. Create a virtual environment and install dev dependencies.
2. Launch the app with `python -m app.main`.
3. Select a CSV/XLSX source file and confirm preview/header warnings.
4. Connect and introspect PostgreSQL metadata.
5. Auto-map tables, then review/edit column mappings.
6. Run validation and confirm any blocking/warning issues.
7. Run dry-run and confirm row counts.
8. Run insert only against a disposable database.

## Packaging

```bash
pyinstaller packaging/pyinstaller/etl-loader.spec
```

Build and verify artifacts on each target OS rather than cross-compiling.

## Transaction Strategy

Runtime loading currently supports only all-or-nothing transactional inserts. The saved-job `transaction_strategy` field is retained for compatibility, but `per_table` partial-commit behavior is not implemented.
