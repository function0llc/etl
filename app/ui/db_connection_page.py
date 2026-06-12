from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSpinBox, QVBoxLayout, QWidget

from app.core.db_connection import create_postgres_engine, dispose_engine, get_password, save_password, test_connection
from app.core.db_introspection import introspect_database
from app.core.job_store import load_profiles, save_profiles
from app.core.models import ConnectionProfile


class DbConnectionPage(QWidget):
    def __init__(self, state: dict, on_changed) -> None:
        super().__init__()
        self.state = state
        self.on_changed = on_changed
        self.saved_profiles = QComboBox()
        self.saved_profiles.currentTextChanged.connect(self._load_selected_profile)
        self.name = QLineEdit("default")
        self.host = QLineEdit("localhost")
        self.port = QSpinBox()
        self.port.setRange(1, 65535)
        self.port.setValue(5432)
        self.database = QLineEdit()
        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.schema = QLineEdit("public")
        self.status = QLabel("Connect to PostgreSQL to introspect metadata.")

        form = QFormLayout()
        form.addRow("Saved profiles", self.saved_profiles)
        for label, widget in [("Profile", self.name), ("Host", self.host), ("Port", self.port), ("Database", self.database), ("Username", self.username), ("Password", self.password), ("Default schema", self.schema)]:
            form.addRow(label, widget)

        save_button = QPushButton("Save Profile")
        save_button.clicked.connect(self.save_current_profile)
        test = QPushButton("Test and Introspect")
        test.clicked.connect(self.connect_db)

        actions = QHBoxLayout()
        actions.addWidget(save_button)
        actions.addWidget(test)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(actions)
        layout.addWidget(self.status)
        self._refresh_saved_profiles()

    def connect_db(self) -> None:
        profile = self._profile_from_fields()
        ok, message = test_connection(profile, self.password.text())
        if not ok:
            self.status.setText(f"Connection failed: {message}")
            return

        self.save_current_profile(update_status=False)
        previous_engine = self.state.get("engine")
        engine = create_postgres_engine(profile, self.password.text())
        try:
            metadata = introspect_database(engine)
        except Exception as exc:
            dispose_engine(engine)
            self.status.setText(f"Introspection failed: {type(exc).__name__}")
            return

        dispose_engine(previous_engine)
        self.state.pop("metadata", None)
        self.state.pop("mappings", None)
        self.state.pop("validation", None)
        self.state.update({"profile": profile, "engine": engine, "metadata": metadata})
        self.status.setText(f"Connected. Introspected {len(metadata.tables)} tables/views.")
        self.on_changed()

    def save_current_profile(self, update_status: bool = True) -> None:
        profile = self._profile_from_fields()
        if self.password.text():
            save_password(profile, self.password.text())
        else:
            existing = next((item for item in load_profiles() if item.name == profile.name), None)
            if existing and existing.password_key:
                profile.password_key = existing.password_key

        profiles = [item for item in load_profiles() if item.name != profile.name]
        profiles.append(profile)
        save_profiles(profiles)
        self._refresh_saved_profiles(selected_name=profile.name)
        if update_status:
            self.status.setText(f"Saved profile '{profile.name}'.")

    def _profile_from_fields(self) -> ConnectionProfile:
        existing = next((item for item in load_profiles() if item.name == self.name.text()), None)
        return ConnectionProfile(
            self.name.text(),
            self.host.text(),
            self.port.value(),
            self.database.text(),
            self.username.text(),
            default_schema=self.schema.text() or None,
            password_key=existing.password_key if existing else None,
        )

    def _load_selected_profile(self, profile_name: str) -> None:
        if not profile_name:
            return
        profile = next((item for item in load_profiles() if item.name == profile_name), None)
        if profile is None:
            return
        self.name.setText(profile.name)
        self.host.setText(profile.host)
        self.port.setValue(profile.port)
        self.database.setText(profile.database)
        self.username.setText(profile.username)
        self.schema.setText(profile.default_schema or "")
        self.password.setText(get_password(profile) or "")
        self.status.setText(f"Loaded profile '{profile.name}'.")

    def _refresh_saved_profiles(self, selected_name: str | None = None) -> None:
        profile_names = sorted(profile.name for profile in load_profiles())
        self.saved_profiles.blockSignals(True)
        self.saved_profiles.clear()
        self.saved_profiles.addItem("")
        self.saved_profiles.addItems(profile_names)
        if selected_name and selected_name in profile_names:
            self.saved_profiles.setCurrentText(selected_name)
        self.saved_profiles.blockSignals(False)
