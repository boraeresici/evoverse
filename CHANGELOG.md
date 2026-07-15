# Changelog

All notable changes to Evoverse are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to
follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

See [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) for the design and approach, and `docs/` for API contracts.

## [Unreleased]

### Added

- **Correlation-length & organism-pattern diagnostics** (design
  [`docs/CORRELATION_AND_PATTERNS.md`](docs/CORRELATION_AND_PATTERNS.md)). A read-only,
  deterministic measurement layer in `backend/app/simulation/diagnostics.py`, wired
  into the benchmark CLI, that answers "can the system reproduce the starling
  scale-free correlation, and capture recurring organism patterns?" empirically:
  **(A)** a correlation length ξ over region-field fluctuations (mean-subtracted, C(r)
  first zero-crossing) plus a `scale_free_scan` across world sizes with a
  `critical`/`sub_critical`/`super_critical` verdict and data-collapse error;
  **(B)** a pattern census that captures and *counts* recurring motifs — morphotypes
  (with a convergent-evolution index), spatial tilings, a domain-size power-law fit,
  lineage motifs, and event n-grams — each with distinct/entropy/effective-count;
  **(C)** conditional triggers, a lift table joining each motif to the state (era,
  region bands, collapse, catalyst) it forms under, in static and deterministic-replay
  trace modes. New benchmark flags `--correlation --patterns --triggers --scale-free
  --sizes --field --trace`; the default benchmark and determinism signature are
  unchanged. Covered by `backend/tests/test_diagnostics.py`. The measured verdict on
  the current engine tuning is `sub_critical` (short-range correlation) — an honest
  "not scale-free in this regime", not biological validation.
- **Chirality field (T1) — inheritance, selection, and symmetry-break events**
  (design §6.2–6.3, §7). Lineages now carry a handedness (`Species.chirality`,
  −1/0/+1) that is adopted one-way from the origin region's locked hand ("chiral
  central dogma") and inherited at speciation, with a rare, near-always-lethal
  chiral-flip mutation. Heterochiral selection taxes the growth of a committed
  lineage sitting in an opposite-hand region and is lethal past a load threshold
  (an uncommitted lineage is never penalized). A new `SYMMETRY_BREAK` event marks
  the universe's first molecular break, each lineage committing a hand, and the
  universe reaching full homochirality. Surfaced on the API (`chirality`,
  `heterochiralLoad` on species), persisted (migration `010_species_chirality.sql`
  + species snapshot payload), and covered by `backend/tests/test_chirality.py`.
  New editable `ChiralityRules` knobs: `inheritFlipChance`,
  `heterochiralGrowthPenalty`, `heterochiralLethalLoad`, `heterochiralLethalDecline`.
  Rule loading now also tolerates configs predating individual rule fields (not
  just whole sections), falling back to field defaults.

### Fixed

- **Worker loop no longer degrades or errors out over time.** The persistence hot
  path was O(event history) on every tick: `load_alpha` hydrated the entire event
  log into memory, and `save_alpha` deduped writes with an `id IN (<all events>)`
  clause that eventually blew past the DB driver's bind-parameter limit (constant
  errors) after progressively freezing. Fixes: tail-load only the newest
  `MAX_LOADED_EVENTS`, an append watermark bounded by `MAX(tick)`, optional
  `MAX_STORED_EVENTS` retention pruning, and hot-path indexes
  (`migrations/009_loop_hotpath_indexes.sql`). New env knobs
  `EVOVERSE_MAX_LOADED_EVENTS` (default 2000) and `EVOVERSE_MAX_STORED_EVENTS`
  (default 0 = unlimited). See [`docs/PERFORMANCE_LOOP.md`](docs/PERFORMANCE_LOOP.md).

## [0.4.0] - 2026-07-15

### Added

- **Chirality field (T1)** — a symmetry-breaking *maturity* subsystem inspired by
  S. Furkan Ozturk & Dimitar Sasselov's biological-homochirality research. Each
  region carries an enantiomeric excess (`chirality_ee`, −1..+1) that drifts through
  a pitchfork bifurcation, latches irreversibly once it crosses the lock threshold,
  and avalanches its hand to neighbours; the universe exposes `homochirality_index`
  (mean |ee|) as a single maturity metric. New editable `ChiralityRules` section flows
  through the `/admin/config` draft → validate → apply → rollback path, with a
  backward-compatible fallback so stored configs predating the section still load.
  Surfaced on the API (`chiralityEe`, `homochiralityIndex`, `chiralityLocked` on the
  universe and regions), persisted (migration `008_chirality_field.sql`, plus snapshot
  payloads for time travel), and included in the determinism signature. Covered by
  `backend/tests/test_chirality.py`.
- **Design note** [`docs/CHIRALITY_AND_MIND.md`](docs/CHIRALITY_AND_MIND.md) — the full
  spec: field/rule schema, the two-tier "life → mind" (cognitive homochirality)
  framing, the Era gate, the three.js Organism Lens hooks, and the scientific
  references. Linked from the README, `docs/DEVELOPMENT.md`, and the resources shelf,
  which now cites Ozturk's publications as orientation points.

## [0.3.7] - 2026-07-04

### Fixed

- An account listed in `EVOVERSE_AUTH_BOOTSTRAP_ADMINS` was not granted admin if
  a role row already existed for it (e.g. a lower or inactive grant created
  before the id was added to the allowlist). The admin baseline only inserted
  when no row existed, so a stale row silently blocked promotion. The baseline
  now repairs env-declared admins to an active `admin` role on startup, without
  ever downgrading an existing admin.

## [0.3.6] - 2026-07-04

### Fixed

- After signing in with Google, the Admin config page could still show "Admin
  access required" for an admin account. The auth-state-dependent nav links
  (`/auth`, `/admin/config`) used Next.js default prefetch, so a logged-out
  prefetch could cache a session-less render that survived sign-in. Those links
  now use `prefetch={false}`, and the admin page is `force-dynamic` so it always
  renders against the live session cookie.

### Changed

- The admin gate now distinguishes three states instead of always claiming the
  user lacks the admin role: "Sign in required" (no session reached the backend),
  "Access could not be verified" (session active but the role check failed —
  reload to retry), and the authenticated-but-not-admin denial (now naming the
  signed-in identity). This makes a missing/blocked session obvious instead of
  reading as an authorization failure.

## [0.3.5] - 2026-07-04

### Fixed

- Google sign-in redirected to the internal container host (e.g.
  `https://0.0.0.0:3000/auth?status=signed-in`) instead of the public domain.
  Behind a reverse proxy (Traefik/Cloudflare) `request.url` reflects the
  internal origin, so the auth routes now build redirects and the OAuth
  `redirect_uri` from a new `publicOrigin()` helper that reads the
  `x-forwarded-proto`/`x-forwarded-host` (falling back to `host`) headers.
  Session and OAuth-state cookies also derive their `secure` flag from the
  forwarded scheme, so they are marked secure over the public HTTPS origin.

## [0.3.4] - 2026-07-04

### Fixed

- Deployed pages showed "Alpha signal is stabilizing" (empty states) even though
  the backend was reachable and serving data. Server-side reads in `lib/api.ts`
  used `NEXT_PUBLIC_API_URL` (empty in production, since the browser talks
  same-origin), so they fetched a relative URL and failed. They now prefer the
  server-only `EVOVERSE_API_URL` (like the BFF routes), using `||` so an empty
  value falls through to the default.

## [0.3.3] - 2026-07-04

### Fixed

- Compose deploy failed with `Bind for 0.0.0.0:8000 failed: port is already
  allocated` on shared hosts. `docker-compose.yaml` no longer publishes host ports;
  services talk over the internal network (`backend`/`frontend` use `expose`), and
  managed hosts (Coolify) route the domain to the `frontend` service via their proxy.

### Added

- `docker-compose.override.yaml` republishes host ports (postgres `5433`, backend
  `8000`, frontend `3000`) for local development. `docker compose` merges it, but an
  explicit `-f docker-compose.yaml` (as Coolify runs) ignores it — so the deploy
  stays internal-only.

### Changed

- Renamed `docker-compose.yml` to `docker-compose.yaml` (Coolify's default name;
  still recognized by the docker compose CLI).

## [0.3.2] - 2026-07-04

Public-demo hardening: a lockable admin surface and live streaming that works
without exposing the backend to the browser.

### Added

- **`EVOVERSE_ALLOW_LOCAL_ADMIN`** — when `false` (default outside `local`, and in
  the demo compose), the local fallback identity holds no admin role: `/admin/config`
  is gated and every admin write returns `403`, while observer/catalyst still work.
- **Same-origin live stream** — the browser now connects to `/api/events/stream`
  and `/api/chronicle` (BFF proxies) instead of the backend directly, so live
  chronicle streaming works with the backend kept internal (no CORS, no public API
  host). `LiveChronicle` no longer uses `NEXT_PUBLIC_API_URL`.
- **`EVOVERSE_CORS_ORIGINS`** — the API CORS allowlist is now env-configurable
  (still defaults to localhost); only needed if a browser calls the API cross-origin.

### Changed

- The demo `docker-compose.yaml` locks admin and destructive ops by default while
  keeping observer/catalyst interaction open.

## [0.3.1] - 2026-07-04

Deployment scaffolding — the full-stack app was failing to deploy because the
monorepo root was being built as a single Node app.

### Added

- `frontend/Dockerfile` (Next.js standalone) and `backend/Dockerfile` (FastAPI;
  reused for the worker), plus `.dockerignore` files and `backend/requirements.txt`.
- Full-stack `docker-compose.yaml` (postgres + backend + worker + frontend) for a
  one-command deploy on Docker-Compose hosts.
- Frontend `start` script, `output: "standalone"` in `next.config.mjs`, and a
  `node >= 20` engines hint.
- README "Deployment" section and updated operations guidance.

### Changed

- `docker-compose.yaml` postgres no longer mounts migrations as init scripts; the
  migration runner (`make migrate` / backend start command) is the single path,
  avoiding double-apply.

### Fixed

- Deployments that built the repo root now have per-service Docker builds that
  succeed (verified by building and running both images).

## [0.3.0] - 2026-07-03

First public release. Operations readiness, an admin auth boundary, a help
system, and open-source preparation.

### Added

- **Micro life authenticity (Paket 22).** The Micro Life Field now models real
  births and deaths: a persistent agent pool reconciles against the projection so
  population growth spawns agents (a spark that scales in) and decline fades them
  out, instead of re-seeding. A toggleable legend maps the visual language
  (hue → species, drift → mobility, clustering → cooperation, brightness → energy,
  ripples → events).
- **Operations & production readiness (Paket 17).** Worker graceful shutdown
  (clean stop on SIGTERM/SIGINT); a destructive-ops guard so seed reset returns
  `403` unless explicitly enabled; worker staleness/state in
  `/admin/simulation/health`; an Operations panel on `/admin/config`; and
  `docs/OPERATIONS_PLAYBOOK.md` (deployment, migration, backup/recovery).
- **Admin auth boundary.** `/admin/config` is gated on the admin role — non-admin
  identities see a restricted panel instead of the editor and operations controls,
  complementing the backend write gate.
- **Help system.** A markdown-driven FAQ at `/faq` (`frontend/content/faq.md`,
  extensible), expandable per-page help (`PageHelp`), and accessible `(i)` info
  tooltips on key metrics.
- **`docs/DEVELOPMENT.md`** — a consolidated English design-and-approach essay.

### Changed

- Footer mark is `STUDIOBINARY [B01]`; footer and README note the 2025–2026
  development period.
- README summarizes Purpose and References and links the essay that references
  Evoverse.

### Removed / internal

- Internal Turkish planning docs and the sprint tracker are excluded from the
  public repository (moved under `internal/` and git-ignored).

### License

- Released under the MIT License.

## [0.2.3] - 2026-07-03

Experience track (Paket 21): species forecast becomes a visual trajectory.

### Added

- **Forecast visualization (Paket 21).** `ForecastPanel` (server component, pure
  SVG) replaces the bare forecast percentages on species detail with radial
  gauges (extinction / dominance / expansion / mutation, each with a
  Stable/Elevated/Critical hint) plus a population **fan chart**: the observed
  population line, a forward confidence band, a projected median, and a "now"
  divider.
- `frontend/lib/forecast.ts`: gauge mapping and an illustrative population
  projection derived from forecast signals (net expansion − extinction drift; the
  fan widens with mutation volatility and extinction risk). This is a
  visualization, not a backend simulation.

### Removed

- The bare `forecast-grid` / `ForecastMetric` percentages on species detail.

## [0.2.2] - 2026-07-03

Experience track (Paket 20): the universe map becomes spatially faithful.

### Added

- **Spatial universe map (Paket 20).** `UniverseExplorer` replaces the
  array-order square grid with a hexagon honeycomb laid out from each region's
  `x`/`y` coordinates (`frontend/lib/hexMap.ts`, pointy-top odd-r offset), so
  neighbouring regions are actually adjacent and spread reads spatially. The same
  layout drives the time-travel snapshot redraw.
- **Neighbour event waves.** Activity ripples outward from regions with recent
  events to their hex neighbours via multi-source BFS ring distance
  (`eventWaveRings`), with ring-delayed glow.
- **Stability breathing.** The whole map breathes at a rate tied to global mean
  stability (calmer when stable); live regions pulse with a hex heartbeat. All
  motion respects `prefers-reduced-motion`.

### Changed

- The region cell is split into an outer positioning box and an inner clipped
  `.region-hex` body so the hexagon `clip-path` never clips the hover tooltip.

## [0.2.1] - 2026-07-03

Experience track (Paket 19): the species lineage view becomes a real
time-axis phylogenetic tree.

### Added

- **Phylogenetic evolution tree (Paket 19).** The single-level `EvolutionGraph`
  (Paket 15) is replaced by `PhylogeneticTree` on the species detail page:
  x = emergence world age, y = lineage. Species render as horizontal lifelines;
  children branch off the parent lifeline at their own emergence age, making
  radiation visible.
  - Bounded tree construction in `frontend/lib/phylogeny.ts` (ancestor chain +
    siblings + capped descendant BFS) with tidy row assignment.
  - Extinct branches fade, dash, and terminate with an extinction cap; emergence
    dots, major-mutation markers on the selected lineage, an Alpha Age axis, a
    legend, and an "N of M species" coverage readout.
  - The selected species is center-focused (halo); other nodes navigate to their
    species page.

### Changed

- The Evolution section on species detail is now full-width ("Phylogenetic Tree")
  to give the time-axis tree room.

## [0.2.0] - 2026-07-03

The observatory grows from a data panel into a living, time-travelable artificial
ecosystem: authenticated identity behind a BFF, an editable rules admin surface,
richer species replay/evolution, an engagement digest, and universe-map time
navigation.

### Added

- **Auth & identity (Paket 13A–13E).** `/me/identity` role bridge; session/header
  identity resolver (`x-evoverse-user-id` / `-observer-id` / `-catalyst-id` /
  `-admin-id`); admin write gate (403 for guests); auth provider/env contract with
  invite bootstrap admins/catalysts; production fallback guard (401 when
  `EVOVERSE_AUTH_ALLOW_LOCAL_FALLBACK=false`); trusted-header BFF boundary
  (`EVOVERSE_AUTH_TRUSTED_HEADER_SECRET`); Google OAuth route wiring
  (`/api/auth/google`, `/api/auth/callback/google`, `/api/auth/logout`, `/auth`) with
  HTTP-only session cookies.
- **Client mutation cleanup (Paket 13E).** Follow/unfollow, notification read, and
  catalyst actions moved behind same-origin BFF routes (`/api/observer/*`,
  `/api/catalyst/action`); the browser no longer carries local `userId`/`actorId`.
  Server relay in `lib/serverApi.ts` with `EVOVERSE_API_URL` override.
- **Editable rules admin UI (Paket 14).** `/admin/config` is now a writable editor
  (draft → validate → apply → rollback) with partial-payload writes, risky-change
  preview and confirm gate, revision/audit history with restore, and hot-reload
  strategy visibility. Admin rule mutations go through `/api/admin/rules/*` BFF routes.
- **Replay & evolution deepening (Paket 15).** SVG phylogenetic-style evolution graph
  with navigable nodes; categorized, clickable population-chart event markers
  (emergence / major mutation / extinction / decline / collapse / catalyst); replay
  playback with progress and category legend; shareable PNG species card
  (`lib/speciesCard.ts`) plus JSON export.
- **Notification & engagement loop (Paket 16).** Following Digest on `/notifications`
  (per-entity summary cards, cross-entity highlights, Daily/Weekly/All-time windows);
  notification inbox unread + category filtering with tones; `POST
  /me/notifications/read-all` bulk mark (+ BFF route).
- **Time navigation (Paket 18).** Persistent universe-map time scrubber
  (`TimeScrubber` + `UniverseTimeExplorer`) driven by snapshot frames: draggable
  history, Era band, population sparkline, cinematic Play, Live return, Time Zoom
  presets, and log-axis toggle. The map redraws from historical snapshots via the
  same-origin `GET /api/snapshots/{tick}/details` proxy.
- **Micro Life View & Genesis (Paket 11–12).** Deterministic sampled Micro Life Field
  on region detail; report-bridged projection; `/genesis` narrative with a canvas
  seed-preview stage.
- **Frontend experience.** Dynamic report panel, region comparison, universe map
  modes, search, region/species detail panels, chronicle filters, and live chronicle
  SSE with polling fallback.

### Changed

- `GET /admin/simulation/rules` now reports `mode: editable`, `uiEditable: true`,
  `writeSurface: api_and_admin_ui`.
- Species detail export upgraded from JSON-only to a visual/shareable card.

### Fixed

- Usage guide modal was trapped inside the `backdrop-filter` header; it now portals to
  `document.body` and covers the viewport correctly.
- Time-navigation snapshot reads were blocked by the narrow backend CORS allowlist;
  they now route through a same-origin BFF proxy so the browser never calls the API
  cross-origin.

### Notes

- Era bands and the Daily/Weekly digest cadence use placeholder world-age constants;
  the literal tick→calendar mapping remains an open product decision.
- Operations/production hardening (Paket 17) is intentionally sequenced behind the
  experience track (Paket 18–22).

## [0.1.0]

Initial development slice.

### Added

- FastAPI backend with product endpoints and a deterministic Alpha tick engine.
- PostgreSQL-backed persistence: append-only event store, current-state snapshots,
  optimistic tick conflict guard, worker heartbeat, `GET /admin/simulation/health`.
- Snapshot strategy: `universe_snapshots` summaries plus `region_snapshots`,
  `species_snapshots`, `population_snapshots` detail coverage; snapshot list/latest/
  details endpoints; Dynamic Report v1.
- Simulation rules config, catalyst limits, speciation/collapse thresholds, and the
  10,000-tick benchmark CLI.
- Chronicle / region / species event pagination with versioned payload envelopes and
  realtime SSE delivery.
- Observer follows, in-app notifications, and catalyst action/role backend.
- SQL migration runner with a `schema_migrations` checksum ledger.
- Next.js frontend scaffold for the Smart Observatory landing.
