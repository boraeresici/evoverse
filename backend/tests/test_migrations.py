from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text

from app.persistence.migrations import (
    MigrationChecksumError,
    discover_migrations,
    migration_status,
    upgrade,
)


def test_discovers_initial_sql_migration() -> None:
    migrations = discover_migrations()

    assert len(migrations) == 13
    assert migrations[0].version == "001"
    assert migrations[0].name == "initial_schema"
    assert len(migrations[0].checksum) == 64
    assert "CREATE TABLE IF NOT EXISTS universes" in migrations[0].sql
    assert migrations[1].version == "002"
    assert migrations[1].name == "simulation_rule_governance"
    assert migrations[2].version == "003"
    assert migrations[2].name == "entity_snapshot_details"
    assert "CREATE TABLE IF NOT EXISTS region_snapshots" in migrations[2].sql
    assert migrations[3].version == "004"
    assert migrations[3].name == "observer_notifications"
    assert "CREATE TABLE IF NOT EXISTS observer_follows" in migrations[3].sql
    assert migrations[4].version == "005"
    assert migrations[4].name == "catalyst_roles_results"
    assert "CREATE TABLE IF NOT EXISTS catalyst_user_roles" in migrations[4].sql
    assert migrations[5].version == "006"
    assert migrations[5].name == "admin_simulation_controls"
    assert "CREATE TABLE IF NOT EXISTS admin_simulation_runs" in migrations[5].sql
    assert migrations[6].version == "007"
    assert migrations[6].name == "observability_analytics"
    assert "CREATE TABLE IF NOT EXISTS api_request_logs" in migrations[6].sql
    assert "CREATE TABLE IF NOT EXISTS product_analytics_events" in migrations[6].sql
    assert migrations[7].version == "008"
    assert migrations[7].name == "chirality_field"
    assert "ADD COLUMN IF NOT EXISTS chirality_ee" in migrations[7].sql
    assert migrations[8].version == "009"
    assert migrations[8].name == "loop_hotpath_indexes"
    assert "idx_events_universe_tick" in migrations[8].sql
    assert migrations[9].version == "010"
    assert migrations[9].name == "species_chirality"
    assert "ADD COLUMN IF NOT EXISTS chirality" in migrations[9].sql
    assert migrations[10].version == "011"
    assert migrations[10].name == "event_feed_keyset_indexes"
    assert "idx_events_region_tick" in migrations[10].sql
    assert migrations[11].version == "012"
    assert migrations[11].name == "snapshot_frame_budget"
    assert "idx_universe_snapshots_universe_tick" in migrations[11].sql
    assert migrations[12].version == "013"
    assert migrations[12].name == "diagnostics_runs"
    assert "CREATE TABLE IF NOT EXISTS diagnostics_runs" in migrations[12].sql


def test_upgrade_applies_pending_sql_migrations(tmp_path) -> None:
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    (migrations_dir / "001_create_widgets.sql").write_text(
        """
        CREATE TABLE widgets (
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL
        );
        """,
        encoding="utf-8",
    )
    (migrations_dir / "002_seed_widgets.sql").write_text(
        """
        INSERT INTO widgets (id, name) VALUES ('alpha', 'Alpha');
        """,
        encoding="utf-8",
    )
    database_url = f"sqlite+pysqlite:///{tmp_path / 'alpha.db'}"

    result = upgrade(database_url, migrations_dir)
    states = migration_status(database_url, migrations_dir)

    assert [migration.version for migration in result.applied] == ["001", "002"]
    assert [state.status for state in states] == ["applied", "applied"]

    engine = create_engine(database_url, future=True)
    with engine.begin() as connection:
        widget = connection.execute(text("SELECT name FROM widgets")).scalar_one()
        recorded = connection.execute(text("SELECT COUNT(*) FROM schema_migrations")).scalar_one()

    assert widget == "Alpha"
    assert recorded == 2


def test_upgrade_rejects_changed_applied_migration(tmp_path) -> None:
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    migration_path = migrations_dir / "001_create_widgets.sql"
    migration_path.write_text(
        "CREATE TABLE widgets (id TEXT PRIMARY KEY);",
        encoding="utf-8",
    )
    database_url = f"sqlite+pysqlite:///{tmp_path / 'alpha.db'}"

    upgrade(database_url, migrations_dir)
    migration_path.write_text(
        "CREATE TABLE widgets (id TEXT PRIMARY KEY, name TEXT);",
        encoding="utf-8",
    )

    with pytest.raises(MigrationChecksumError):
        upgrade(database_url, migrations_dir)
