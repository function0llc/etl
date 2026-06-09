from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any, Literal


@dataclass
class SourceSheet:
    name: str
    headers: list[str]
    row_count: int
    duplicate_headers: list[str] = field(default_factory=list)
    empty_headers: list[str] = field(default_factory=list)


@dataclass
class SourceDataset:
    file_path: str
    file_type: Literal["csv", "xlsx"]
    sheets: dict[str, Any]
    metadata: dict[str, SourceSheet]


@dataclass
class ConnectionProfile:
    name: str
    host: str
    port: int
    database: str
    username: str
    ssl_mode: str | None = None
    default_schema: str | None = "public"
    password_key: str | None = None


@dataclass
class ColumnDefinition:
    schema: str
    table: str
    name: str
    data_type: str
    nullable: bool
    has_default: bool
    max_length: int | None = None
    numeric_precision: int | None = None
    numeric_scale: int | None = None
    enum_values: list[str] | None = None
    is_primary_key: bool = False
    is_identity: bool = False
    is_generated: bool = False


@dataclass
class UniqueConstraint:
    schema: str
    table: str
    name: str
    columns: list[str]


@dataclass
class ForeignKey:
    schema: str
    table: str
    columns: list[str]
    referred_schema: str
    referred_table: str
    referred_columns: list[str]


@dataclass
class TableDefinition:
    schema: str
    name: str
    columns: list[ColumnDefinition]
    primary_key: list[str] = field(default_factory=list)
    unique_constraints: list[UniqueConstraint] = field(default_factory=list)
    foreign_keys: list[ForeignKey] = field(default_factory=list)
    is_view: bool = False


@dataclass
class DatabaseMetadata:
    schemas: list[str]
    tables: dict[tuple[str, str], TableDefinition]


@dataclass
class ColumnMapping:
    source_column: str | None
    target_column: str
    transform: str | None = None
    constant_value: Any | None = None


@dataclass
class TableMapping:
    source_sheet: str
    target_schema: str
    target_table: str
    column_mappings: list[ColumnMapping] = field(default_factory=list)


@dataclass
class EtlJob:
    name: str
    source_file_path: str
    connection_profile_name: str
    table_mappings: list[TableMapping]
    transaction_strategy: Literal["all_or_nothing", "per_table"] = "all_or_nothing"
    load_mode: Literal["dry_run", "insert_only"] = "dry_run"


@dataclass
class ValidationError:
    source_sheet: str
    target_schema: str
    target_table: str
    row_number: int
    source_column: str | None
    target_column: str | None
    original_value: Any
    transformed_value: Any
    error_type: str
    message: str
    severity: Literal["blocking", "warning"] = "blocking"


@dataclass
class ValidationResult:
    errors: list[ValidationError]
    transformed_rows: dict[tuple[str, str, str], list[dict[str, Any]]]

    @property
    def has_blocking_errors(self) -> bool:
        return any(error.severity == "blocking" for error in self.errors)


@dataclass
class LoadSummary:
    dry_run: bool
    inserted_counts: dict[str, int]
    elapsed_seconds: float
    message: str


def to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return {key: to_jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    return value
