from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from app.core.validation import validate_job


class ValidationWorker(QObject):
    progress = Signal(str)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, dataset, metadata, mappings, engine=None) -> None:
        super().__init__()
        self.dataset = dataset
        self.metadata = metadata
        self.mappings = mappings
        self.engine = engine
        self._cancelled = False

    @Slot()
    def run(self) -> None:
        try:
            if self._cancelled:
                self.failed.emit("Validation cancelled")
                return
            self.progress.emit("Validating rows")
            result = validate_job(self.dataset, self.metadata, self.mappings, self.engine)
            self.finished.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))

    @Slot()
    def cancel(self) -> None:
        self._cancelled = True
