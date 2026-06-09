from __future__ import annotations

from PySide6.QtWidgets import QFormLayout, QLabel, QLineEdit, QPushButton, QSpinBox, QVBoxLayout, QWidget

from app.core.db_connection import create_postgres_engine, save_password, test_connection
from app.core.db_introspection import introspect_database
from app.core.job_store import load_profiles, save_profiles
from app.core.models import ConnectionProfile


class DbConnectionPage(QWidget):
    def __init__(self, state: dict, on_changed) -> None:
        super().__init__()
        self.state = state
        self.on_changed = on_changed
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
        for label, widget in [("Profile", self.name), ("Host", self.host), ("Port", self.port), ("Database", self.database), ("Username", self.username), ("Password", self.password), ("Default schema", self.schema)]:
            form.addRow(label, widget)
        test = QPushButton("Test and Introspect")
        test.clicked.connect(self.connect_db)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(test)
        layout.addWidget(self.status)

    def connect_db(self) -> None:
        profile = ConnectionProfile(self.name.text(), self.host.text(), self.port.value(), self.database.text(), self.username.text(), default_schema=self.schema.text() or None)
        ok, message = test_connection(profile, self.password.text())
        if not ok:
            self.status.setText(f"Connection failed: {message}")
            return
        if self.password.text():
            save_password(profile, self.password.text())
            profiles = [item for item in load_profiles() if item.name != profile.name]
            profiles.append(profile)
            save_profiles(profiles)
        engine = create_postgres_engine(profile, self.password.text())
        metadata = introspect_database(engine)
        self.state.update({"profile": profile, "engine": engine, "metadata": metadata})
        self.status.setText(f"Connected. Introspected {len(metadata.tables)} tables/views.")
        self.on_changed()
