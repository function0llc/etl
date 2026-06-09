from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from app.config.settings import setup_logging
from app.ui.main_window import MainWindow


def main() -> int:
    setup_logging()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
