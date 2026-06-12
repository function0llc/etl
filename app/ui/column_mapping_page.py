from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QLabel, QLineEdit, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from app.core.mapping import required_columns, source_options_for_sheet, target_columns_for_mapping, update_column_mapping
from app.core.transforms import UI_TRANSFORMS


class ColumnMappingPage(QWidget):
    def __init__(self, state: dict, on_changed) -> None:
        super().__init__()
        self.state = state
        self.on_changed = on_changed
        self.status = QLabel("Column mappings can be edited after table mapping.")
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Source sheet", "Target column", "Required", "Source column", "Transform", "Constant value", "Status"]
        )
        self._last_signature: tuple[Any, ...] | None = None
        self._populating = False
        layout = QVBoxLayout(self)
        layout.addWidget(self.status)
        layout.addWidget(self.table)

    def refresh(self) -> None:
        mappings = self.state.get("mappings") or []
        metadata = self.state.get("metadata")
        dataset = self.state.get("dataset")
        signature = (
            tuple(
                (
                    mapping.source_sheet,
                    mapping.target_schema,
                    mapping.target_table,
                    tuple(
                        (
                            col_map.target_column,
                            col_map.source_column,
                            col_map.transform,
                            None if col_map.constant_value is None else str(col_map.constant_value),
                        )
                        for col_map in mapping.column_mappings
                    ),
                )
                for mapping in mappings
            ),
            bool(metadata),
            bool(dataset),
        )
        if self._last_signature == signature:
            return

        self._populating = True
        self.table.setRowCount(0)
        for mapping_index, mapping in enumerate(mappings):
            table_def = metadata.tables.get((mapping.target_schema, mapping.target_table)) if metadata else None
            if table_def is None:
                continue
            sheet = dataset.metadata.get(mapping.source_sheet) if dataset else None
            source_options = source_options_for_sheet(sheet) if sheet else []
            required_names = {column.name for column in required_columns(table_def, mapping.column_mappings)}

            by_target = {col_map.target_column: col_map for col_map in mapping.column_mappings}
            for target_column in target_columns_for_mapping(table_def):
                col_map = by_target.get(target_column.name)
                row = self.table.rowCount()
                self.table.insertRow(row)
                self._set_read_only_item(row, 0, mapping.source_sheet)
                self._set_read_only_item(row, 1, target_column.name)

                required = (not target_column.nullable) and (not target_column.has_default)
                self._set_read_only_item(row, 2, "Yes" if required else "No")

                source_combo = QComboBox()
                source_combo.addItem("")
                source_combo.addItems(source_options)
                source_combo.blockSignals(True)
                source_combo.setCurrentText(col_map.source_column if col_map and col_map.source_column else "")
                source_combo.blockSignals(False)

                transform_combo = QComboBox()
                transform_combo.addItem("")
                transform_combo.addItems(UI_TRANSFORMS)
                transform_combo.blockSignals(True)
                transform_combo.setCurrentText(col_map.transform if col_map and col_map.transform else "")
                transform_combo.blockSignals(False)

                constant_input = QLineEdit()
                constant_input.setPlaceholderText("constant value")
                constant_input.setText("" if col_map is None or col_map.constant_value is None else str(col_map.constant_value))

                if transform_combo.currentText() == "constant_value":
                    source_combo.setCurrentIndex(0)
                    source_combo.setEnabled(False)

                source_combo.currentIndexChanged.connect(
                    lambda _value, m=mapping_index, target=target_column.name, src=source_combo, tr=transform_combo, const=constant_input: self._on_mapping_change(
                        m, target, src, tr, const
                    )
                )
                transform_combo.currentIndexChanged.connect(
                    lambda _value, m=mapping_index, target=target_column.name, src=source_combo, tr=transform_combo, const=constant_input: self._on_mapping_change(
                        m, target, src, tr, const
                    )
                )
                constant_input.editingFinished.connect(
                    lambda m=mapping_index, target=target_column.name, src=source_combo, tr=transform_combo, const=constant_input: self._on_mapping_change(
                        m, target, src, tr, const
                    )
                )

                self.table.setCellWidget(row, 3, source_combo)
                self.table.setCellWidget(row, 4, transform_combo)
                self.table.setCellWidget(row, 5, constant_input)

                status = self._status_for_row(col_map, target_column.name in required_names)
                self._set_read_only_item(row, 6, status)

        self._populating = False
        self._last_signature = signature
        self.status.setText(f"{self.table.rowCount()} editable column mapping row(s).")

    def _on_mapping_change(
        self,
        mapping_index: int,
        target_column: str,
        source_combo: QComboBox,
        transform_combo: QComboBox,
        constant_input: QLineEdit,
    ) -> None:
        if self._populating:
            return

        mappings = self.state.get("mappings") or []
        if mapping_index >= len(mappings):
            return

        transform = transform_combo.currentText() or None
        source_column = source_combo.currentText() or None
        if transform == "constant_value":
            source_column = None
            source_combo.blockSignals(True)
            source_combo.setCurrentIndex(0)
            source_combo.blockSignals(False)
            source_combo.setEnabled(False)
        else:
            source_combo.setEnabled(True)

        constant_text = constant_input.text()
        constant_value: object | None = constant_text if constant_text != "" else None

        mappings[mapping_index] = update_column_mapping(
            mappings[mapping_index],
            target_column=target_column,
            source_column=source_column,
            transform=transform,
            constant_value=constant_value,
        )
        self.state["mappings"] = mappings
        self.state.pop("validation", None)
        self._last_signature = None
        self.refresh()
        self.on_changed()

    @staticmethod
    def _status_for_row(col_map: Any, required_missing: bool) -> str:
        if required_missing:
            return "Missing required mapping"
        if col_map is None:
            return "Optional"
        if col_map.transform == "constant_value":
            return "Mapped (constant)"
        if col_map.source_column:
            return "Mapped"
        return "Optional"

    def _set_read_only_item(self, row: int, column: int, value: str) -> None:
        item = QTableWidgetItem(value)
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, column, item)
