# Operations Playbook

Production and recovery runbook for Evoverse Alpha. Companion to
`docs/ADMIN_SIMULATION_CONTROLS.md` (admin API) and `docs/SNAPSHOT_STRATEGY.md`.

## Deployment model

Alpha runs as three long-lived processes plus a database:

| Process | Command | Role |
| --- | --- | --- |
| API | `uvicorn app.main:app --app-dir backend` | Serves reads/writes; refreshes Alpha from Postgres on read. |
| Worker | `python -m app.worker` | Advances the simulation and writes state back to Postgres. |
| Frontend | `npm --prefix frontend run build && start` | Next.js app; browser talks only to same-origin `/api/*` BFF routes. |
| Postgres | (managed) | Durable shared state for API + worker. |

Key property: **API and worker share state only through Postgres.** With
`EVOVERSE_PERSISTENCE=memory` each process has its own in-memory universe, so a
real deployment must use `EVOVERSE_PERSISTENCE=postgres`. The admin
`/admin/simulation/health` `persistence` field and the Operations panel on
`/admin/config` surface this.

### Concurrency

The worker is designed to run as a **single instance**. Repository writes use an
optimistic tick guard (`AlphaStateConflictError`), so a second worker fails its
write instead of corrupting state, but running one worker is the supported model.
Run it under a process manager that keeps exactly one replica (systemd unit,
Kubernetes `Deployment` with `replicas: 1`, or a single container).

### Graceful shutdown

The worker installs SIGTERM/SIGINT handlers: on signal it finishes the current
step, records a `complete` run event with `stoppedBy: "signal"`, and exits 0.
Orchestrators that send SIGTERM before SIGKILL get a clean stop that does not look
like a crash in the run ledger.

## Environment matrix

| Variable | Local default | Production guidance |
| --- | --- | --- |
| `EVOVERSE_ENV` | `local` | `production` |
| `EVOVERSE_PERSISTENCE` | `memory` | `postgres` |
| `EVOVERSE_DATABASE_URL` | — | required |
| `EVOVERSE_AUTH_ALLOW_LOCAL_FALLBACK` | `true` | `false` |
| `EVOVERSE_AUTH_TRUSTED_HEADER_SECRET` | empty | set (BFF ↔ API secret) |
| `EVOVERSE_ALLOW_DESTRUCTIVE_OPS` | `true` | `false` |
| `EVOVERSE_WORKER_STALE_SECONDS` | `30` | tune to `interval × ~5` |
| `EVOVERSE_WORKER_INTERVAL_SECONDS` | `2` | per throughput target |

`EVOVERSE_ALLOW_DESTRUCTIVE_OPS` and `EVOVERSE_AUTH_ALLOW_LOCAL_FALLBACK` default
to safe values (`false`) whenever `EVOVERSE_ENV` is not `local`.

## Worker health

`GET /admin/simulation/health` returns an `operations` block:

```json
{
  "worker": { "workerId": "...", "status": "running", "lastStep": 42, "updatedAt": "..." },
  "workerStaleSeconds": 2.1,
  "operations": {
    "env": "production",
    "destructiveOpsAllowed": false,
    "workerStaleThresholdSeconds": 30,
    "workerStale": false,
    "workerState": "healthy"
  }
}
```

`workerState` is one of `healthy`, `stale`, `error`, `stopped`, `unknown`. Alert
when it is `stale` or `error` for more than one interval. The Operations panel on
`/admin/config` renders the same data.

## Seed / reset safety

Destructive reset (`POST /admin/simulation/reset`) requires: active admin role,
`confirmReset: true`, **and** `EVOVERSE_ALLOW_DESTRUCTIVE_OPS=true`. When the flag
is off the endpoint returns HTTP `403` regardless of role. Reset preserves
governance data (rules revisions, audit, catalyst roles, run ledger) and, when
`preserveUserState` is true, observer follows and notification reads.

To run a controlled reset in production: temporarily set
`EVOVERSE_ALLOW_DESTRUCTIVE_OPS=true`, restart the API, perform the reset with a
reason, then set it back to `false` and restart.

## Migration procedure

1. Back up first (see below).
2. `make migrate-status` — review pending / checksum-mismatch states.
3. `make migrate` — applies ordered SQL from `backend/migrations` via the
   `schema_migrations` checksum ledger. Migrations are idempotent-friendly and the
   ledger prevents double-apply.
4. Restart API and worker.

A `checksum_mismatch` means a previously applied migration file was edited — never
edit an applied migration; add a new one instead.

## Backup and recovery

Backup (durable state lives entirely in Postgres):

```bash
pg_dump "$EVOVERSE_DATABASE_URL" -Fc -f evoverse-$(date +%Y%m%d).dump
```

Restore into a fresh database, then run migrations if restoring a schema-only
baseline:

```bash
pg_restore --clean --if-exists -d "$EVOVERSE_DATABASE_URL" evoverse-YYYYMMDD.dump
```

### Recovery runbook

- **Stalled worker** (`workerState: stale`): check worker logs and `last_error` on
  the heartbeat; restart the worker process. The optimistic tick guard makes a
  restart safe. State is intact in Postgres.
- **Worker error loop** (`workerState: error`): the worker records the error and
  exits non-zero; the process manager restarts it. If it crashes repeatedly on the
  same tick, inspect `worker_run_events` for the error and consider a rules
  rollback (`/admin/simulation/rules/rollback`) if a bad rule apply caused it.
- **Corrupt / bad state**: restore the latest `pg_dump`, or reset from seed (see
  Seed / reset safety) if history can be discarded.
- **API returns stale data**: the API refreshes from Postgres on read; if it looks
  frozen, confirm the worker is advancing (`workerState`) and that both point at
  the same `EVOVERSE_DATABASE_URL`.

## Observability

- `/admin/simulation/health` — universe, worker, and operations status.
- `/admin/observability/summary` — request/error/worker/analytics summary
  (`docs/OBSERVABILITY_ANALYTICS.md`).
- HTTP middleware records request duration/status/request-id and `>=400` errors.
- Worker lifecycle events are recorded in `worker_run_events`.
