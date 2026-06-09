from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from app.core.loader import load_validated_rows


class LoadWorker(QObject):
    progress = Signal(str)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, engine, validation_result, dry_run: bool = False) -> None:
        super().__init__()
        self.engine = engine
        self.validation_result = validation_result
        self.dry_run = dry_run
        self._cancelled = False

    @Slot()
    def run(self) -> None:
        try:
            self.progress.emit("Loading rows" if not self.dry_run else "Running dry run")
            summary = load_validated_rows(self.engine, self.validation_result, self.dry_run, lambda: self._cancelled)
            self.finished.emit(summary)
        except Exception as exc:
            self.failed.emit(str(exc))

    @Slot()
    def cancel(self) -> None:
        self._cancelled = True
