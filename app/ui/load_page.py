from __future__ import annotations

from PySide6.QtCore import QThread
from PySide6.QtWidgets import QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget

from app.workers.load_worker import LoadWorker


class LoadPage(QWidget):
    def __init__(self, state: dict, on_changed) -> None:
        super().__init__()
        self.state = state
        self.on_changed = on_changed
        self.thread = None
        self.worker = None
        self.status = QLabel("Load is enabled after validation passes.")
        self.summary = QTextEdit()
        self.summary.setReadOnly(True)
        dry_run = QPushButton("Dry Run")
        dry_run.clicked.connect(lambda: self.load(True))
        load = QPushButton("Insert Rows")
        load.clicked.connect(lambda: self.load(False))
        layout = QVBoxLayout(self)
        layout.addWidget(dry_run)
        layout.addWidget(load)
        layout.addWidget(self.status)
        layout.addWidget(self.summary)

    def load(self, dry_run: bool) -> None:
        validation = self.state.get("validation")
        engine = self.state.get("engine")
        if not validation or not engine:
            self.status.setText("Run validation first.")
            return
        if validation.has_blocking_errors:
            self.status.setText("Blocking validation errors prevent load.")
            return
        self.thread = QThread()
        self.worker = LoadWorker(engine, validation, dry_run)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self._finished)
        self.worker.failed.connect(self._failed)
        self.worker.finished.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.start()

    def _finished(self, summary) -> None:
        self.status.setText(summary.message)
        lines = [f"Dry run: {summary.dry_run}", f"Elapsed seconds: {summary.elapsed_seconds:.2f}"]
        lines.extend(f"{table}: {count}" for table, count in summary.inserted_counts.items())
        self.summary.setPlainText("\n".join(lines))
        self.on_changed()

    def _failed(self, message: str) -> None:
        self.status.setText(f"Load failed and transaction was rolled back: {message}")
