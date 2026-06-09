from __future__ import annotations

from PySide6.QtWidgets import QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget


class ColumnMappingPage(QWidget):
    def __init__(self, state: dict, on_changed) -> None:
        super().__init__()
        self.state = state
        self.on_changed = on_changed
        self.status = QLabel("Column auto-mappings appear after table mapping.")
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Source sheet", "Source column", "Target column", "Transform"])
        layout = QVBoxLayout(self)
        layout.addWidget(self.status)
        layout.addWidget(self.table)

    def refresh(self) -> None:
        mappings = self.state.get("mappings") or []
        self.table.setRowCount(0)
        for mapping in mappings:
            for col_map in mapping.column_mappings:
                row = self.table.rowCount()
                self.table.insertRow(row)
                values = [mapping.source_sheet, col_map.source_column or "", col_map.target_column, col_map.transform or ""]
                for col, value in enumerate(values):
                    self.table.setItem(row, col, QTableWidgetItem(value))
        self.status.setText(f"{self.table.rowCount()} column mapping(s).")
