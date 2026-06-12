from __future__ import annotations

from PySide6.QtCore import QThread
from PySide6.QtWidgets import QFileDialog, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from app.core.validation import export_validation_errors
from app.workers.validation_worker import ValidationWorker


class ValidationPage(QWidget):
    def __init__(self, state: dict, on_changed) -> None:
        super().__init__()
        self.state = state
        self.on_changed = on_changed
        self.thread = None
        self.worker = None
        self.status = QLabel("Run validation before loading.")
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["Severity", "Sheet", "Table", "Row", "Column", "Type", "Message"])
        self.validate_button = QPushButton("Validate")
        self.validate_button.clicked.connect(self.validate)
        export = QPushButton("Export Errors")
        export.clicked.connect(self.export_errors)
        layout = QVBoxLayout(self)
        layout.addWidget(self.validate_button)
        layout.addWidget(export)
        layout.addWidget(self.status)
        layout.addWidget(self.table)

    def validate(self) -> None:
        if self.thread is not None:
            return
        if not all(self.state.get(key) for key in ["dataset", "metadata", "mappings"]):
            self.status.setText("Validation requires source, DB metadata, and mappings.")
            return
        self.validate_button.setEnabled(False)
        self.status.setText("Validation running...")
        self.thread = QThread()
        self.worker = ValidationWorker(self.state["dataset"], self.state["metadata"], self.state["mappings"], self.state.get("engine"))
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.status.setText)
        self.worker.finished.connect(self._finished)
        self.worker.failed.connect(self._failed)
        self.worker.finished.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.failed.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self._reset_worker_state)
        self.thread.start()

    def _finished(self, result) -> None:
        self.state["validation"] = result
        self.table.setRowCount(0)
        for error in result.errors:
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = [
                error.severity,
                error.source_sheet,
                f"{error.target_schema}.{error.target_table}",
                str(error.row_number),
                error.target_column or "",
                error.error_type,
                error.message,
            ]
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(value))
        blocking_count = sum(1 for error in result.errors if error.severity == "blocking")
        warning_count = len(result.errors) - blocking_count
        self.status.setText(
            f"Validation complete: {blocking_count} blocking, {warning_count} warning, {len(result.errors)} total."
        )
        self.on_changed()

    def _failed(self, message: str) -> None:
        self.status.setText(f"Validation failed: {message}")

    def _reset_worker_state(self) -> None:
        self.thread = None
        self.worker = None
        self.validate_button.setEnabled(True)

    def export_errors(self) -> None:
        validation = self.state.get("validation")
        if not validation:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export validation errors", "validation-errors.csv", "CSV files (*.csv)")
        if path:
            export_validation_errors(validation.errors, path)
