from __future__ import annotations

import argparse
import signal
import socket
import time
from types import FrameType
from uuid import uuid4

from app.config import get_settings
from app.persistence import create_alpha_repository
from app.services import AlphaStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Evoverse Alpha simulation worker.")
    parser.add_argument("--steps", type=int, default=None)
    parser.add_argument("--ticks", type=int, default=None)
    parser.add_argument("--interval", type=float, default=None)
    parser.add_argument("--worker-id", default=None)
    args = parser.parse_args()

    settings = get_settings()
    if not settings.use_postgres or not settings.database_url:
        raise SystemExit("EVOVERSE_PERSISTENCE=postgres and EVOVERSE_DATABASE_URL are required for the worker.")

    repository = create_alpha_repository(settings.database_url)
    store = AlphaStore(
        seed=settings.seed,
        boot_ticks=settings.boot_ticks,
        repository=repository,
        refresh_on_read=True,
    )

    ticks_per_step = args.ticks or settings.worker_ticks_per_step
    interval = args.interval if args.interval is not None else settings.worker_interval_seconds
    max_steps = args.steps if args.steps is not None else settings.worker_max_steps
    worker_id = args.worker_id or f"{socket.gethostname()}-{uuid4().hex[:8]}"
    repository.record_worker_run_event(
        worker_id=worker_id,
        universe_id="alpha",
        event_type="start",
        status="running",
        payload={
            "ticksPerStep": ticks_per_step,
            "intervalSeconds": interval,
            "maxSteps": max_steps,
        },
    )

    # Graceful shutdown: on SIGTERM/SIGINT finish the current step, then record a
    # clean stop so container/orchestrator restarts do not look like crashes.
    stop = {"requested": False}

    def request_stop(signum: int, _frame: FrameType | None) -> None:
        stop["requested"] = True
        print(f"worker_signal={signum} worker={worker_id} draining", flush=True)

    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, request_stop)

    step = 0
    while (max_steps is None or step < max_steps) and not stop["requested"]:
        step += 1
        try:
            health = store.advance(ticks=ticks_per_step)
            repository.record_worker_heartbeat(
                worker_id=worker_id,
                universe_id=health["universe"],
                status="running",
                last_tick=health["tick"],
                last_world_age=health["ageYears"],
                last_step=step,
            )
            print(
                "worker_step="
                f"{step} worker={worker_id} age={health['ageYears']} tick={health['tick']} "
                f"species={health['species']} events={health['events']}",
                flush=True,
            )
        except Exception as exc:
            repository.record_worker_heartbeat(
                worker_id=worker_id,
                universe_id="alpha",
                status="error",
                last_tick=0,
                last_world_age=0,
                last_step=step,
                last_error=str(exc),
            )
            repository.record_worker_run_event(
                worker_id=worker_id,
                universe_id="alpha",
                event_type="error",
                status="error",
                last_step=step,
                error=str(exc),
            )
            raise
        if (max_steps is None or step < max_steps) and not stop["requested"]:
            time.sleep(interval)
    health = store.health()
    repository.record_worker_run_event(
        worker_id=worker_id,
        universe_id=health["universe"],
        event_type="complete",
        status="stopped",
        last_tick=health["tick"],
        last_world_age=health["ageYears"],
        last_step=step,
        payload={"stoppedBy": "signal" if stop["requested"] else "max_steps"},
    )


if __name__ == "__main__":
    main()
