# Evoverse

Evoverse is a persistent artificial life observatory. The product starts with Alpha: a seeded universe where regions, species, populations, and chronicle events evolve through a deterministic tick engine.

🌐 <a href="https://evoverse.studiobinary.co" target="_blank" rel="noreferrer"><b>Live demo — evoverse.studiobinary.co</b></a> (test environment)

**Version:** 0.3.2 · Planned and built 2025–2026 by Bora ERESICI (StudioBinary) · See [`CHANGELOG.md`](CHANGELOG.md) for release history and [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) for the design and approach.

## What's Inside (0.2.0)

Alpha is now a living, time-travelable observatory rather than a data panel:

- **Deterministic simulation core** — aggregate region/species/population model, catalyst influence, speciation and collapse/recovery, benchmarked over 10,000 ticks.
- **Persistence & snapshots** — PostgreSQL-backed append-only event store, current-state and tick-level snapshots, Dynamic Report, and realtime chronicle SSE.
- **Authenticated identity behind a BFF** — session/header identity resolver, admin role gate, Google OAuth wiring, and same-origin `/api/*` BFF routes so the browser never carries local ids or calls the API cross-origin.
- **Editable rules admin** — `/admin/config` draft → validate → apply → rollback with risky-change preview, revision/audit history, and hot-reload visibility.
- **Living species surfaces** — Micro Life Field, a time-axis phylogenetic tree (radiation + extinction on an Alpha Age axis), categorized replay markers, forecast gauges with a population fan chart, and a shareable PNG species card.
- **Engagement loop** — Following Digest and a filterable notification inbox with bulk mark-read.
- **Time navigation** — a persistent universe-map scrubber with Era bands, cinematic replay, and Time Zoom that redraws the map from historical snapshots.
- **Spatial universe map** — a hexagon honeycomb laid out from region coordinates, with activity waves rippling to neighbours and a global-stability breathing pulse.

## Architecture

- **Backend** (`backend/`): FastAPI + a separate simulation worker, sharing Alpha through PostgreSQL.
- **Frontend** (`frontend/`): Next.js App Router. Browser mutations and cross-origin reads are proxied through same-origin `/api/*` BFF routes that attach trusted session headers server-side.
- **Docs** (`docs/`): API contracts, the operations playbook, and [`DEVELOPMENT.md`](docs/DEVELOPMENT.md) — the design and scientific/engineering approach.

## Purpose & References

**Purpose** (see [`/purpose`](frontend/content/purpose.md)): make artificial life observable, explainable, and product-ready. Evoverse starts from the spirit of Conway's Game of Life — a seeded grid, discrete ticks, local rules, emergence read over time — but it is **not** a binary B3/S23 clone. Each map cell is raised into a *region aggregate* (energy, resources, stability, collapse state, dominant species, population composition) so the product can answer richer questions: what changed, where a species moved, why a region collapsed, and whether the universe is becoming more stable. The relationship to Conway is deliberate lineage, not replication: shared grid/tick/emergence, different (ecological, explainable, historical) model.

**References** (see [`/resources`](frontend/content/resources.md)): orientation points, not endorsements or copied content — Conway's Game of Life & ConwayLife.com (cellular automata origin), NASA Astrobiology and Darwin's *On the Origin of Species* (biology/evolution), and the International Society for Artificial Life (current ALife research). Alpha deliberately combines cellular automata, artificial-life ecology, resource dynamics, event sourcing, snapshot comparison, and observer/catalyst interaction — less mathematically minimal than Life, more legible as a product.

**Related writing** by Bora ERESICI:

- [Evoverse: Not Creating a World, but Witnessing One](https://medium.com/@eresicibora/evoverse-bir-d%C3%BCnyay%C4%B1-yaratmak-de%C4%9Fil-ona-tan%C4%B1kl%C4%B1k-etmek-b7be7bcf5f30) — on the observe-don't-command stance.
- [God at the Interface: An Essay on Being, Nothingness, and the Evolutionary, Philological, and Cognitive Origins of Belief](https://medium.com/@eresicibora/aray%C3%BCzdeki-tanr%C4%B1-varl%C4%B1k-hi%C3%A7lik-ve-inanc%C4%B1n-evrimsel-filolojik-ve-bili%C5%9Fsel-k%C3%B6kenleri-%C3%BCzerine-bir-7c1ace03adea) — references Evoverse.

## Local Development

```bash
cp .env.example .env
docker compose up -d postgres
make migrate
make backend
make frontend
```

Backend: http://localhost:8000

Frontend: http://localhost:3000

PostgreSQL is exposed on host port `5433` by default to avoid colliding with a local system PostgreSQL on `5432`. If any default port is taken, run each service on a free port and point the frontend at the backend with `EVOVERSE_API_URL` (server-only, used by the BFF routes; falls back to `NEXT_PUBLIC_API_URL`). Auth runs in local-fallback mode by default (`EVOVERSE_AUTH_ALLOW_LOCAL_FALLBACK=true`); see `.env.example` and `docs/AUTH_ROLE_GATE_DECISION.md` for the Google OAuth and trusted-header contract.

Simulation worker:

```bash
make worker
```

The API and worker are separate processes. With `EVOVERSE_PERSISTENCE=postgres`, the API refreshes Alpha from PostgreSQL on reads, while the worker advances Alpha and writes the resulting universe, regions, species, populations, events, and active catalyst actions back to PostgreSQL.

Database migrations:

```bash
make migrate-status
make migrate
```

The current migration path uses ordered SQL files in `backend/migrations` plus a `schema_migrations` ledger table with checksums. `make migrate` (or, in containers, the backend startup command) is the single migration path. Alembic is intentionally deferred until schema churn or downgrade/autogeneration needs justify the extra framework surface.

## Deployment

Evoverse is a full-stack app (Next.js frontend + FastAPI backend + a simulation worker sharing PostgreSQL). It deploys as **separate services**, not one — building the monorepo root as a single app will fail.

Each service has a Dockerfile:

- `frontend/Dockerfile` — Next.js standalone production server (port 3000).
- `backend/Dockerfile` — FastAPI API; the same image runs the worker with `python -m app.worker`.

One-command full stack (also suitable for Docker-Compose-based hosts such as Coolify):

```bash
docker compose up --build
```

That starts `postgres`, `backend` (runs migrations then serves on 8000), `worker`, and `frontend` (on 3000, reaching the backend at `http://backend:8000` via `EVOVERSE_API_URL`). The browser only ever talks to the frontend origin — live chronicle streaming is proxied through `/api/events/stream`, so the backend stays internal (no CORS, no public API host).

For a **public demo**, the compose defaults lock the admin surface (`EVOVERSE_ALLOW_LOCAL_ADMIN=false`) and destructive ops (`EVOVERSE_ALLOW_DESTRUCTIVE_OPS=false`) while keeping observer/catalyst interaction open. Set `EVOVERSE_ALLOW_LOCAL_ADMIN=true` (or wire real auth) for a private instance.

For platform (Railway/Render/Coolify) service-per-app setups, point each service at its Dockerfile:

- **Backend**: `backend/Dockerfile`; set `EVOVERSE_PERSISTENCE=postgres`, `EVOVERSE_DATABASE_URL`, and run migrations on start (`python -m app.persistence.migrations upgrade`).
- **Worker**: same image, command `python -m app.worker`.
- **Frontend**: `frontend/Dockerfile`; set `EVOVERSE_API_URL` to the backend's internal URL.

See `docs/OPERATIONS_PLAYBOOK.md` for the deployment model, environment matrix, and recovery runbook.

## Verification

```bash
make test
make smoke
make benchmark
make migrate-status
```

## Product Notes

The UI must avoid exposing raw ticks or simulation internals to users. Public surfaces show Alpha Age, era, species, regions, stability, population, and event language. Debug and admin tooling can expose lower-level details later.

## Backend Hardening Notes

- API and worker can share Alpha through PostgreSQL-backed persistence.
- Event records are append-only; current state saves no longer delete Chronicle history.
- Universe, region, and species tables act as current-state snapshots.
- `universe_snapshots` stores tick-level summary snapshots separately from the event store.
- `region_snapshots`, `species_snapshots`, and `population_snapshots` store entity-level detail coverage for selected Time Zoom, Replay Lite, and Dynamic Report reads. The strategy is documented in `docs/SNAPSHOT_STRATEGY.md`.
- Repository writes support optimistic tick checks so stale API/worker writes fail instead of silently overwriting newer simulation state.
- Workers write heartbeat records that are surfaced through `GET /admin/simulation/health`.
- Latest Alpha snapshot is exposed through `GET /universes/alpha/snapshots/latest`.
- Time Zoom Lite can page Alpha snapshots through `GET /universes/alpha/snapshots?limit=50&offset=0`, with optional `fromAge` and `toAge` filters.
- Snapshot details are exposed through `GET /universes/alpha/snapshots/{tick}/details`.
- Dynamic Report v1 is exposed through `GET /universes/alpha/reports/dynamic` for universe, region, species, and population comparison data. The contract is documented in `docs/DYNAMIC_REPORT_API.md`.
- Chronicle, region event, and species event endpoints support `limit` and `offset` pagination while preserving the existing `events` response field.
- Forecast Lite is exposed through `GET /species/{id}/forecast` and matches the deterministic forecast embedded in species detail responses.
- Simulation thresholds and Catalyst limits are centralized in `backend/app/simulation/rules.py`.
- Region drift uses equilibrium reversion and collapse recovery so long benchmark runs keep Alpha viable instead of collapsing every region.
- Speciation and population growth are tuned against the default 10,000 tick benchmark to avoid runaway species generation after recovery.
- Read-only simulation rules are exposed through `GET /admin/simulation/rules` and surfaced in the frontend at `/admin/config`.
- Rules edit prerequisites are available through guarded admin APIs: `POST /admin/simulation/rules/validate`, `POST /admin/simulation/rules/apply`, `POST /admin/simulation/rules/rollback`, `GET /admin/simulation/rules/audit`, and `GET /admin/simulation/rules/revisions`.
- Rules changes are validated server-side, recorded in an audit log, stored as revisions, and can be rolled back. The frontend remains read-only until the editable admin UI is intentionally opened.
- Admin simulation controls are exposed through `GET /admin/simulation/controls`, `POST /admin/simulation/batches`, `POST /admin/simulation/reset`, and `GET /admin/simulation/runs`. The contract is documented in `docs/ADMIN_SIMULATION_CONTROLS.md`.
- Chronicle event payloads use the versioned v1 envelope documented in `docs/EVENT_PAYLOAD_SCHEMAS.md`; legacy persisted payloads are normalized on backend load.
- `make benchmark` runs the default 10,000 tick benchmark and prints duration, event count, species count, collapsed region count, and a determinism signature.
- `make migrate` applies ordered SQL migrations from `backend/migrations`; `make migrate-status` reports applied, pending, or checksum mismatch states.
- Catalyst actions are invite/role gated, rate-limited by user/action/day, and protected by region cooldowns.
- `GET /me/catalyst/status` exposes Catalyst permission, quota, and cooldown state for the current user.
- `POST /catalyst/actions` accepts `regionId`, `actionType`, and optional `userId`; role failures return HTTP 403, cooldown and quota failures return HTTP 429, and accepted actions return result tracking metadata.
- Catalyst role/result tracking is documented in `docs/CATALYST_API.md`.
- Observability and analytics are exposed through `GET /admin/observability/summary`, request/error log endpoints, worker event history, and `POST /analytics/events`. The contract is documented in `docs/OBSERVABILITY_ANALYTICS.md`.
- API errors use a standard envelope: `{"error":{"code":"not_found","message":"Region not found","status":404}}`.

## Experience & Auth Notes (0.2.0)

- Identity is resolved from session/header context; admin write endpoints require an active admin role. Provider, fallback, trusted-header, and Google OAuth env contract are documented in `docs/AUTH_ROLE_GATE_DECISION.md`.
- The browser calls only same-origin `/api/*` BFF routes; those forward trusted session headers to the backend. This covers observer/catalyst mutations, admin rule mutations, notification bulk-read, and historical snapshot reads.
- The editable rules admin UI at `/admin/config` supports draft/validate/apply/rollback with risky-change preview; the same-origin routes are `/api/admin/rules/{validate,apply,rollback}` plus `/history`.
- `POST /me/notifications/read-all` bulk-marks observer notifications; the `/notifications` page renders a Following Digest built from follows + notifications.
- The Universe map time scrubber reads historical snapshots through `GET /api/snapshots/{tick}/details`; the time-navigation strategy is documented in `docs/SNAPSHOT_STRATEGY.md`.

## License

Released under the [MIT License](LICENSE).
