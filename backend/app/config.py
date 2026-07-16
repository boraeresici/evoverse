from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def load_dotenv_file(path: Path | None = None) -> None:
    env_path = path or Path.cwd() / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


@dataclass(frozen=True)
class Settings:
    env: str
    seed: int
    database_url: str | None
    persistence: str
    boot_ticks: int
    auth_provider: str
    auth_allow_local_fallback: bool
    auth_trusted_header_secret: str | None
    auth_google_client_id: str | None
    auth_google_client_secret: str | None
    auth_bootstrap_admins: tuple[str, ...]
    auth_bootstrap_catalysts: tuple[str, ...]
    api_refresh_on_read: bool
    worker_interval_seconds: float
    worker_ticks_per_step: int
    worker_max_steps: int | None
    worker_compact_every_steps: int
    allow_destructive_ops: bool
    worker_stale_seconds: float
    allow_local_admin: bool
    cors_origins: tuple[str, ...]

    @property
    def use_postgres(self) -> bool:
        return self.persistence == "postgres" and bool(self.database_url)


def get_settings() -> Settings:
    load_dotenv_file()
    env = os.getenv("EVOVERSE_ENV", "local")
    auth_provider = _auth_provider(os.getenv("EVOVERSE_AUTH_PROVIDER", "local"))
    return Settings(
        env=env,
        seed=int(os.getenv("EVOVERSE_SEED", "4211")),
        database_url=os.getenv("EVOVERSE_DATABASE_URL"),
        persistence=os.getenv("EVOVERSE_PERSISTENCE", "memory"),
        boot_ticks=int(os.getenv("EVOVERSE_BOOT_TICKS", "96")),
        auth_provider=auth_provider,
        auth_allow_local_fallback=_as_bool(
            os.getenv("EVOVERSE_AUTH_ALLOW_LOCAL_FALLBACK", "true" if env == "local" else "false")
        ),
        auth_trusted_header_secret=os.getenv("EVOVERSE_AUTH_TRUSTED_HEADER_SECRET") or None,
        auth_google_client_id=os.getenv("EVOVERSE_GOOGLE_CLIENT_ID") or None,
        auth_google_client_secret=os.getenv("EVOVERSE_GOOGLE_CLIENT_SECRET") or None,
        auth_bootstrap_admins=_as_csv(os.getenv("EVOVERSE_AUTH_BOOTSTRAP_ADMINS", "local-admin")),
        auth_bootstrap_catalysts=_as_csv(os.getenv("EVOVERSE_AUTH_BOOTSTRAP_CATALYSTS", "local-catalyst")),
        api_refresh_on_read=_as_bool(os.getenv("EVOVERSE_API_REFRESH_ON_READ", "true")),
        worker_interval_seconds=float(os.getenv("EVOVERSE_WORKER_INTERVAL_SECONDS", "2")),
        worker_ticks_per_step=int(os.getenv("EVOVERSE_WORKER_TICKS_PER_STEP", "1")),
        worker_max_steps=_as_optional_int(os.getenv("EVOVERSE_WORKER_MAX_STEPS")),
        # How often the worker sweeps off-stride snapshot frames, in steps. The
        # write path already refuses to add off-stride frames, so this only has to
        # catch up when the stride widens -- rare, since it doubles. It also drains
        # a pre-stride backlog, which is why it runs often enough to make progress
        # without a manual backfill. 0 disables it.
        worker_compact_every_steps=int(os.getenv("EVOVERSE_WORKER_COMPACT_EVERY_STEPS", "30")),
        allow_destructive_ops=_as_bool(
            os.getenv("EVOVERSE_ALLOW_DESTRUCTIVE_OPS", "true" if env == "local" else "false")
        ),
        worker_stale_seconds=float(os.getenv("EVOVERSE_WORKER_STALE_SECONDS", "30")),
        allow_local_admin=_as_bool(
            os.getenv("EVOVERSE_ALLOW_LOCAL_ADMIN", "true" if env == "local" else "false")
        ),
        cors_origins=_as_csv(
            os.getenv("EVOVERSE_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
        ),
    )


def _as_bool(value: str) -> bool:
    return value.lower() in {"1", "true", "yes", "on"}


def _as_optional_int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _auth_provider(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in {"local", "google"}:
        raise ValueError(f"Unsupported EVOVERSE_AUTH_PROVIDER: {value}")
    return normalized


def _as_csv(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(item.strip() for item in value.split(",") if item.strip())
