from __future__ import annotations

import argparse
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from sqlalchemy import Connection, create_engine, text

from app.config import get_settings


DEFAULT_MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"
MIGRATION_TABLE = "schema_migrations"


class MigrationChecksumError(RuntimeError):
    def __init__(self, migration: Migration, applied_checksum: str) -> None:
        self.migration = migration
        self.applied_checksum = applied_checksum
        super().__init__(
            f"Migration {migration.version} checksum changed: "
            f"applied {applied_checksum}, current {migration.checksum}"
        )


@dataclass(frozen=True)
class Migration:
    version: str
    name: str
    path: Path
    checksum: str
    sql: str


@dataclass(frozen=True)
class MigrationState:
    version: str
    name: str
    checksum: str
    applied_checksum: str | None
    status: str


@dataclass(frozen=True)
class MigrationRunResult:
    applied: list[Migration]
    states: list[MigrationState]


def discover_migrations(
    migrations_dir: Path | str = DEFAULT_MIGRATIONS_DIR,
) -> list[Migration]:
    root = Path(migrations_dir)
    migrations: list[Migration] = []
    seen_versions: set[str] = set()
    for path in sorted(root.glob("[0-9][0-9][0-9]_*.sql")):
        version, name = path.stem.split("_", 1)
        if version in seen_versions:
            raise ValueError(f"Duplicate migration version: {version}")
        seen_versions.add(version)
        sql = path.read_text(encoding="utf-8")
        migrations.append(
            Migration(
                version=version,
                name=name,
                path=path,
                checksum=sha256(sql.encode("utf-8")).hexdigest(),
                sql=sql,
            )
        )
    return migrations


def migration_status(
    database_url: str,
    migrations_dir: Path | str = DEFAULT_MIGRATIONS_DIR,
) -> list[MigrationState]:
    engine = create_engine(database_url, future=True)
    with engine.begin() as connection:
        _ensure_migration_table(connection)
        return _migration_states(connection, discover_migrations(migrations_dir))


def upgrade(
    database_url: str,
    migrations_dir: Path | str = DEFAULT_MIGRATIONS_DIR,
) -> MigrationRunResult:
    engine = create_engine(database_url, future=True)
    migrations = discover_migrations(migrations_dir)
    applied_now: list[Migration] = []
    with engine.begin() as connection:
        _ensure_migration_table(connection)
        applied = _applied_migrations(connection)
        for migration in migrations:
            applied_checksum = applied.get(migration.version)
            if applied_checksum is not None:
                if applied_checksum != migration.checksum:
                    raise MigrationChecksumError(migration, applied_checksum)
                continue
            _execute_migration(connection, migration)
            connection.execute(
                text(
                    f"""
                    INSERT INTO {MIGRATION_TABLE} (version, name, checksum)
                    VALUES (:version, :name, :checksum)
                    """
                ),
                {
                    "version": migration.version,
                    "name": migration.name,
                    "checksum": migration.checksum,
                },
            )
            applied_now.append(migration)

        states = _migration_states(connection, migrations)
    return MigrationRunResult(applied=applied_now, states=states)


def _ensure_migration_table(connection: Connection) -> None:
    connection.execute(
        text(
            f"""
            CREATE TABLE IF NOT EXISTS {MIGRATION_TABLE} (
              version TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              checksum TEXT NOT NULL,
              applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )


def _applied_migrations(connection: Connection) -> dict[str, str]:
    rows = connection.execute(
        text(f"SELECT version, checksum FROM {MIGRATION_TABLE}")
    ).mappings()
    return {row["version"]: row["checksum"] for row in rows}


def _migration_states(
    connection: Connection,
    migrations: list[Migration],
) -> list[MigrationState]:
    applied = _applied_migrations(connection)
    states: list[MigrationState] = []
    for migration in migrations:
        applied_checksum = applied.get(migration.version)
        if applied_checksum is None:
            status = "pending"
        elif applied_checksum == migration.checksum:
            status = "applied"
        else:
            status = "checksum_mismatch"
        states.append(
            MigrationState(
                version=migration.version,
                name=migration.name,
                checksum=migration.checksum,
                applied_checksum=applied_checksum,
                status=status,
            )
        )
    return states


def _execute_migration(connection: Connection, migration: Migration) -> None:
    raw_connection = connection.connection.driver_connection
    if connection.dialect.name == "sqlite":
        raw_connection.executescript(migration.sql)
        return
    # Execute with no parameters at all. `exec_driver_sql` always hands psycopg an
    # empty parameter sequence, which switches on placeholder scanning — and that
    # scan is textual, so it does not know `--` starts a comment. A migration that
    # merely *mentions* the modulo operator in prose (012's "tick % stride") dies
    # with "incomplete placeholder: '%'". Migrations are static DDL and never take
    # parameters, so there is nothing to interpolate.
    with raw_connection.cursor() as cursor:
        cursor.execute(migration.sql)


def _database_url_from_args(value: str | None) -> str:
    if value:
        return value
    settings = get_settings()
    if not settings.database_url:
        raise SystemExit("EVOVERSE_DATABASE_URL is required for migrations.")
    return settings.database_url


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Evoverse SQL migrations.")
    parser.add_argument("command", choices=("status", "upgrade"))
    parser.add_argument("--database-url")
    parser.add_argument(
        "--migrations-dir",
        type=Path,
        default=DEFAULT_MIGRATIONS_DIR,
    )
    args = parser.parse_args()

    database_url = _database_url_from_args(args.database_url)
    if args.command == "status":
        states = migration_status(database_url, args.migrations_dir)
        _print_states(states)
        return

    result = upgrade(database_url, args.migrations_dir)
    if result.applied:
        for migration in result.applied:
            print(f"Applied {migration.version}_{migration.name}")
    else:
        print("No pending migrations.")
    _print_states(result.states)


def _print_states(states: list[MigrationState]) -> None:
    for state in states:
        print(
            f"{state.version}_{state.name}: "
            f"{state.status} ({state.checksum[:12]})"
        )


if __name__ == "__main__":
    main()
