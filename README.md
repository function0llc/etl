# ETL Loader

Standalone PySide6 desktop app for loading CSV/XLSX data into PostgreSQL with schema introspection, mapping, validation, dry runs, transactional inserts, saved jobs, keyring-backed connection profiles, and PyInstaller packaging.

## Development

```bash
cd etl_loader
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m app.main
pytest
```

## Packaging

```bash
cd etl_loader
pyinstaller packaging/pyinstaller/etl-loader.spec
```

Build and verify artifacts on each target OS rather than cross-compiling.
