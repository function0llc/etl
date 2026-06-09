from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
import pandas as pd

from app.core.models import SourceDataset, SourceSheet


SUPPORTED_SUFFIXES = {".csv", ".xlsx", ".xlsm"}


def detect_csv_dialect(path: Path, encoding: str = "utf-8") -> csv.Dialect:
    with path.open("r", encoding=encoding, newline="") as file:
        sample = file.read(8192)
    return csv.Sniffer().sniff(sample) if sample else csv.get_dialect("excel")


def _metadata(name: str, frame: pd.DataFrame) -> SourceSheet:
    headers = [str(column) if column is not None else "" for column in frame.columns]
    counts = Counter(header for header in headers if header)
    duplicate_headers = sorted(header for header, count in counts.items() if count > 1)
    empty_headers = [header for header in headers if not header or header.startswith("Unnamed:")]
    return SourceSheet(name=name, headers=headers, row_count=len(frame), duplicate_headers=duplicate_headers, empty_headers=empty_headers)


def load_source_file(path: str, encoding: str = "utf-8", delimiter: str | None = None, preview_rows: int | None = None) -> SourceDataset:
    file_path = Path(path)
    suffix = file_path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError(f"unsupported file type: {suffix}")

    read_kwargs = {"nrows": preview_rows} if preview_rows else {}
    if suffix == ".csv":
        sep = delimiter
        if sep is None:
            try:
                sep = detect_csv_dialect(file_path, encoding).delimiter
            except csv.Error:
                sep = ","
        frame = pd.read_csv(file_path, encoding=encoding, sep=sep, **read_kwargs)
        sheet_name = file_path.stem
        return SourceDataset(
            file_path=str(file_path),
            file_type="csv",
            sheets={sheet_name: frame},
            metadata={sheet_name: _metadata(sheet_name, frame)},
        )

    sheets = pd.read_excel(file_path, sheet_name=None, engine="openpyxl", **read_kwargs)
    return SourceDataset(
        file_path=str(file_path),
        file_type="xlsx",
        sheets=sheets,
        metadata={name: _metadata(name, frame) for name, frame in sheets.items()},
    )


def load_source_file_full(path: str, encoding: str = "utf-8", delimiter: str | None = None) -> SourceDataset:
    file_path = Path(path)
    suffix = file_path.suffix.lower()
    if suffix == ".csv":
        sep = delimiter
        if sep is None:
            try:
                sep = detect_csv_dialect(file_path, encoding).delimiter
            except csv.Error:
                sep = ","
        frame = pd.read_csv(file_path, encoding=encoding, sep=sep)
        sheet_name = file_path.stem
        return SourceDataset(
            file_path=str(file_path),
            file_type="csv",
            sheets={sheet_name: frame},
            metadata={sheet_name: _metadata(sheet_name, frame)},
        )
    return load_source_file(path, encoding=encoding, delimiter=delimiter)


def validate_source_headers(dataset: SourceDataset) -> list[str]:
    messages: list[str] = []
    for sheet in dataset.metadata.values():
        if sheet.duplicate_headers:
            messages.append(f"{sheet.name}: duplicate headers: {', '.join(sheet.duplicate_headers)}")
        if sheet.empty_headers:
            messages.append(f"{sheet.name}: empty headers require explicit mapping")
    return messages
