from __future__ import annotations

from PySide6.QtWidgets import QLabel, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from app.core.mapping import suggest_column_mappings, suggest_table_mapping
from app.core.models import TableMapping


class TableMappingPage(QWidget):
    def __init__(self, state: dict, on_changed) -> None:
        super().__init__()
        self.state = state
        self.on_changed = on_changed
        self.status = QLabel("Table mappings require source data and DB metadata.")
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Source", "Target schema", "Target table"])
        auto = QPushButton("Auto Suggest Mappings")
        auto.clicked.connect(self.auto_map)
        layout = QVBoxLayout(self)
        layout.addWidget(auto)
        layout.addWidget(self.status)
        layout.addWidget(self.table)

    def auto_map(self) -> None:
        dataset = self.state.get("dataset")
        metadata = self.state.get("metadata")
        if not dataset or not metadata:
            self.status.setText("Select a file and connect to DB first.")
            return
        mappings = []
        self.table.setRowCount(0)
        preferred = getattr(self.state.get("profile"), "default_schema", None)
        for sheet in dataset.metadata.values():
            target = suggest_table_mapping(sheet, metadata, preferred)
            if not target:
                continue
            col_maps = suggest_column_mappings(sheet.headers, target.columns)
            mappings.append(TableMapping(sheet.name, target.schema, target.name, col_maps))
            row = self.table.rowCount()
            self.table.insertRow(row)
            for col, value in enumerate([sheet.name, target.schema, target.name]):
                self.table.setItem(row, col, QTableWidgetItem(value))
        self.state["mappings"] = mappings
        self.status.setText(f"Created {len(mappings)} table mapping(s).")
        self.on_changed()
