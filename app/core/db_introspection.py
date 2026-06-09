from __future__ import annotations

from collections import defaultdict

from sqlalchemy import Engine, inspect, text

from app.core.models import ColumnDefinition, DatabaseMetadata, ForeignKey, TableDefinition, UniqueConstraint


def introspect_database(engine: Engine, include_views: bool = False) -> DatabaseMetadata:
    inspector = inspect(engine)
    schemas = sorted(schema for schema in inspector.get_schema_names() if not schema.startswith("pg_") and schema != "information_schema")
    enum_values = _enum_values(engine)
    identity_map = _identity_and_generated(engine)
    tables: dict[tuple[str, str], TableDefinition] = {}

    for schema in schemas:
        table_names = inspector.get_table_names(schema=schema)
        view_names = inspector.get_view_names(schema=schema) if include_views else []
        for table_name in table_names + view_names:
            is_view = table_name in view_names
            pk = inspector.get_pk_constraint(table_name, schema=schema).get("constrained_columns") or []
            unique_constraints = [
                UniqueConstraint(schema=schema, table=table_name, name=item.get("name") or "", columns=item.get("column_names") or [])
                for item in inspector.get_unique_constraints(table_name, schema=schema)
            ]
            fks = [
                ForeignKey(
                    schema=schema,
                    table=table_name,
                    columns=item.get("constrained_columns") or [],
                    referred_schema=item.get("referred_schema") or schema,
                    referred_table=item.get("referred_table") or "",
                    referred_columns=item.get("referred_columns") or [],
                )
                for item in inspector.get_foreign_keys(table_name, schema=schema)
            ]
            columns: list[ColumnDefinition] = []
            for column in inspector.get_columns(table_name, schema=schema):
                identity, generated = identity_map[(schema, table_name)].get(column["name"], (False, False))
                data_type = str(column["type"])
                columns.append(
                    ColumnDefinition(
                        schema=schema,
                        table=table_name,
                        name=column["name"],
                        data_type=data_type,
                        nullable=bool(column.get("nullable", True)),
                        has_default=column.get("default") is not None,
                        max_length=getattr(column["type"], "length", None),
                        numeric_precision=getattr(column["type"], "precision", None),
                        numeric_scale=getattr(column["type"], "scale", None),
                        enum_values=enum_values.get(data_type),
                        is_primary_key=column["name"] in pk,
                        is_identity=identity,
                        is_generated=generated,
                    )
                )
            tables[(schema, table_name)] = TableDefinition(schema, table_name, columns, pk, unique_constraints, fks, is_view)
    return DatabaseMetadata(schemas=schemas, tables=tables)


def _enum_values(engine: Engine) -> dict[str, list[str]]:
    sql = text(
        """
        select t.typname as enum_name, e.enumlabel as enum_value
        from pg_type t
        join pg_enum e on t.oid = e.enumtypid
        order by t.typname, e.enumsortorder
        """
    )
    values: dict[str, list[str]] = defaultdict(list)
    with engine.connect() as conn:
        for row in conn.execute(sql):
            values[row.enum_name].append(row.enum_value)
    return dict(values)


def _identity_and_generated(engine: Engine) -> dict[tuple[str, str], dict[str, tuple[bool, bool]]]:
    sql = text(
        """
        select table_schema, table_name, column_name,
               is_identity = 'YES' as is_identity,
               is_generated != 'NEVER' as is_generated
        from information_schema.columns
        where table_schema not in ('pg_catalog', 'information_schema')
        """
    )
    result: dict[tuple[str, str], dict[str, tuple[bool, bool]]] = defaultdict(dict)
    with engine.connect() as conn:
        for row in conn.execute(sql):
            result[(row.table_schema, row.table_name)][row.column_name] = (row.is_identity, row.is_generated)
    return result
