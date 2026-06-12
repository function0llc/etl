from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from app.core.mapping import suggest_column_mappings, suggest_table_mapping
from app.core.models import TableMapping


class TableMappingPage(QWidget):
    def __init__(self, state: dict, on_changed) -> None:
        super().__init__()
        self.state = state
        self.on_changed = on_changed
        self.status = QLabel("Table mappings require source data and DB metadata.")
        self.schema_select = QComboBox()
        self.schema_select.currentTextChanged.connect(self._render_tables)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Schema", "Table"])
        auto = QPushButton("Auto Suggest Mappings")
        auto.clicked.connect(self.auto_map)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Schema"))
        layout.addWidget(self.schema_select)
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
        preferred = self.schema_select.currentText() or getattr(self.state.get("profile"), "default_schema", None)
        for sheet in dataset.metadata.values():
            target = suggest_table_mapping(sheet, metadata, preferred)
            if not target:
                continue
            col_maps = suggest_column_mappings(sheet.headers, target.columns)
            mappings.append(TableMapping(sheet.name, target.schema, target.name, col_maps))
        self.state["mappings"] = mappings
        selected_schema = preferred or "all schemas"
        self.status.setText(f"Created {len(mappings)} table mapping(s) using {selected_schema} preference.")
        self.on_changed()

    def refresh(self) -> None:
        metadata = self.state.get("metadata")
        if not metadata:
            self.table.setRowCount(0)
            self.schema_select.blockSignals(True)
            self.schema_select.clear()
            self.schema_select.blockSignals(False)
            self.status.setText("Table mappings require source data and DB metadata.")
            return

        schemas = sorted(metadata.schemas)
        preferred = getattr(self.state.get("profile"), "default_schema", None)
        current = self.schema_select.currentText()

        self.schema_select.blockSignals(True)
        self.schema_select.clear()
        self.schema_select.addItems(schemas)
        if current in schemas:
            self.schema_select.setCurrentText(current)
        elif preferred in schemas:
            self.schema_select.setCurrentText(preferred)
        elif schemas:
            self.schema_select.setCurrentIndex(0)
        self.schema_select.blockSignals(False)

        self._render_tables(self.schema_select.currentText())

    def _render_tables(self, schema: str) -> None:
        metadata = self.state.get("metadata")
        if not metadata:
            return

        table_defs = sorted(
            [table for table in metadata.tables.values() if table.schema == schema],
            key=lambda item: item.name,
        )
        self.table.setRowCount(0)
        for table_def in table_defs:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(table_def.schema))
            self.table.setItem(row, 1, QTableWidgetItem(table_def.name))

        self.status.setText(f"{len(table_defs)} table/view item(s) in schema '{schema}'.")
