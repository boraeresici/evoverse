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


SCALE_FREE_SIZES = [(12, 9), (16, 12), (20, 15), (24, 18)]


def _run_scale_free_scan(
    repository,
    seed: int,
    *,
    scan_ticks: int,
    seeds: int,
    universe_tick: int,
    worker_id: str,
    step: int,
) -> None:
    """Measure the scale-free scan and park it. Never fails the loop.

    A diagnostic that kills the simulation it is measuring is worse than no
    diagnostic, so a scan that raises is logged and dropped — the previous row
    stays and the page keeps reporting the last good measurement with its own
    tick attached, which is honest either way.

    ``scan_ticks`` is how deep each replayed world is advanced and is a property of
    the experiment; ``universe_tick`` is how old Alpha was when the experiment ran
    and is context. They used to be the same number, and collapsing them is what let
    the scan's cost grow with the universe forever. Both are stored: the row's
    ``ticks`` is the depth, and the payload carries the universe tick, so the page
    can say what was measured and when without implying the two are one thing.
    """
    from app.simulation.diagnostics import scale_free_scan

    started = time.perf_counter()
    try:
        scan = scale_free_scan(seed, int(scan_ticks), sizes=SCALE_FREE_SIZES, seeds=seeds)
    except Exception as exc:  # noqa: BLE001 - deliberately broad, see docstring
        print(f"worker_scan_failed step={step} worker={worker_id} error={exc}", flush=True)
        return
    duration_ms = (time.perf_counter() - started) * 1000
    scan["universeTick"] = int(universe_tick)
    repository.save_diagnostics_run(
        universe_id="alpha",
        kind="scale_free_scan",
        seed=seed,
        ticks=int(scan_ticks),
        verdict=scan["verdict"],
        duration_ms=round(duration_ms, 3),
        payload=scan,
    )
    slope = scan["slope"]
    print(
        f"worker_scan step={step} worker={worker_id} scan_ticks={scan_ticks} "
        f"seeds={len(scan['seeds'])} universe_tick={universe_tick} "
        f"verdict={scan['verdict']} slope={slope['mean']}+-{slope['se']} "
        f"duration_ms={duration_ms:.0f}",
        flush=True,
    )


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
    compact_every_steps = settings.worker_compact_every_steps
    scan_every_steps = settings.worker_scan_every_steps
    scan_ticks = settings.worker_scan_ticks
    scan_seeds = settings.worker_scan_seeds
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
            # The worker is the only process on a timer, so it owns snapshot
            # compaction. Each call drops at most one batch of frames, so a
            # widening stride settles over a few steps and a pre-stride backlog
            # drains across many -- never in one transaction that would stall the
            # database.
            if compact_every_steps > 0 and step % compact_every_steps == 0:
                compacted = repository.compact_snapshots()
                if compacted["framesDropped"]:
                    print(
                        f"worker_compact step={step} worker={worker_id} "
                        f"stride={compacted['stride']} frames_dropped={compacted['framesDropped']}",
                        flush=True,
                    )
            # The scale-free scan is the one diagnostic a request can never run: it
            # replays four universes under each of several seeds and takes minutes.
            # Measuring it here and parking the row is what lets /science answer its
            # own headline. The cost is fixed by scan_ticks rather than Alpha's tick,
            # so this stays a constant slice of the loop however old the universe gets.
            if scan_every_steps > 0 and step % scan_every_steps == 0:
                _run_scale_free_scan(
                    repository,
                    settings.seed,
                    scan_ticks=scan_ticks,
                    seeds=scan_seeds,
                    universe_tick=health["tick"],
                    worker_id=worker_id,
                    step=step,
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
