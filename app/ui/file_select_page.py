from __future__ import annotations

from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from app.core.file_loader import load_source_file_full, validate_source_headers


class FileSelectPage(QWidget):
    def __init__(self, state: dict, on_changed) -> None:
        super().__init__()
        self.state = state
        self.on_changed = on_changed
        self.path = QLineEdit()
        self.status = QLabel("Select a CSV or XLSX file.")
        self.preview = QTableWidget()
        browse = QPushButton("Browse")
        browse.clicked.connect(self.choose_file)
        row = QHBoxLayout()
        row.addWidget(self.path)
        row.addWidget(browse)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Source File"))
        layout.addLayout(row)
        layout.addWidget(self.status)
        layout.addWidget(self.preview)

    def choose_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select source file", "", "Data files (*.csv *.xlsx *.xlsm)")
        if not path:
            return
        self.path.setText(path)
        try:
            dataset = load_source_file_full(path)
            self.state["dataset"] = dataset
            messages = validate_source_headers(dataset)
            self.status.setText("; ".join(messages) if messages else f"Loaded {len(dataset.sheets)} source table(s)")
            self._render_preview(next(iter(dataset.sheets.values())))
            self.on_changed()
        except Exception as exc:
            self.status.setText(f"File load failed: {exc}")

    def _render_preview(self, frame) -> None:
        preview = frame.head(50)
        self.preview.setRowCount(len(preview))
        self.preview.setColumnCount(len(preview.columns))
        self.preview.setHorizontalHeaderLabels([str(col) for col in preview.columns])
        for row_index, (_, row) in enumerate(preview.iterrows()):
            for column_index, value in enumerate(row):
                self.preview.setItem(row_index, column_index, QTableWidgetItem("" if value is None else str(value)))
