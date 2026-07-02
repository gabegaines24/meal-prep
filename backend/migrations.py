"""Lightweight SQLite migrations for additive schema changes."""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def _add_column_if_missing(engine: Engine, table: str, column: str, ddl: str) -> None:
    insp = inspect(engine)
    if table not in insp.get_table_names():
        return
    existing = {c["name"] for c in insp.get_columns(table)}
    if column in existing:
        return
    with engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))


def run_migrations(engine: Engine) -> None:
    _add_column_if_missing(engine, "recipes", "estimated_cost_per_serving", "estimated_cost_per_serving FLOAT")
    _add_column_if_missing(engine, "recipes", "price_source", "price_source VARCHAR")
    _add_column_if_missing(engine, "user_profile", "zip_code", "zip_code VARCHAR DEFAULT ''")
    _add_column_if_missing(engine, "user_profile", "store_name", "store_name VARCHAR DEFAULT ''")
    _add_column_if_missing(engine, "user_profile", "kroger_location_id", "kroger_location_id VARCHAR DEFAULT ''")
    _add_column_if_missing(engine, "user_profile", "weekly_budget", "weekly_budget FLOAT DEFAULT 0.0")
