from __future__ import annotations

from PySide6.QtWidgets import QListWidget, QMainWindow, QStackedWidget, QWidget, QHBoxLayout

from app.ui.column_mapping_page import ColumnMappingPage
from app.ui.db_connection_page import DbConnectionPage
from app.ui.file_select_page import FileSelectPage
from app.ui.load_page import LoadPage
from app.ui.table_mapping_page import TableMappingPage
from app.ui.validation_page import ValidationPage


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ETL Loader")
        self.resize(1100, 760)
        self.state: dict = {}
        self.nav = QListWidget()
        self.stack = QStackedWidget()
        self.pages = [
            ("File", FileSelectPage(self.state, self.refresh)),
            ("Database", DbConnectionPage(self.state, self.refresh)),
            ("Tables", TableMappingPage(self.state, self.refresh)),
            ("Columns", ColumnMappingPage(self.state, self.refresh)),
            ("Validation", ValidationPage(self.state, self.refresh)),
            ("Load", LoadPage(self.state, self.refresh)),
        ]
        for name, page in self.pages:
            self.nav.addItem(name)
            self.stack.addWidget(page)
        self.nav.currentRowChanged.connect(self._page_changed)
        self.nav.setCurrentRow(0)
        root = QWidget()
        layout = QHBoxLayout(root)
        layout.addWidget(self.nav, 1)
        layout.addWidget(self.stack, 5)
        self.setCentralWidget(root)

    def _page_changed(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        page = self.stack.currentWidget()
        if hasattr(page, "refresh"):
            page.refresh()

    def refresh(self) -> None:
        for _, page in self.pages:
            if hasattr(page, "refresh"):
                page.refresh()
