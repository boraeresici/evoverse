# Changelog

All notable changes to Evoverse are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to
follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

See [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) for the design and approach, and `docs/` for API contracts.

## [Unreleased]

### Changed

- **Collapse is now organic, not a 151-tick clock.** The last scripted beat —
  `_maybe_emit_scripted_collapse`, which forced a region's stability to 0.12 every 151
  ticks and stamped the event `synthetic: true` — is deleted. It survived only because
  stability had no downward channel: its lone depleting term was clamped to
  ~0.00036/tick against a reversion to 0.58, so no region ever reached the 0.16 collapse
  gate on its own. A new depletion→stability coupling (`RegionRules.stabilityDepletion*`,
  threshold 0.22, factor 0.08) taxes stability in proportion to how far a region is drawn
  below the scarcity threshold, so a heavily-consumed region spirals into collapse and
  crosses the gate on a noise dip. Measured (20k ticks, base seed): **32 organic
  collapses at irregular 11–2,737-tick gaps** (was 132 on a fixed 151 grid), the
  chronicle is **100% organic** (no `synthetic` flag anywhere), and the world settles at
  ~40k individuals / 134 species — below the ~92k it carries with collapse suppressed,
  which is the real ecological cost of a collapse that now actually kills. Parameters
  were chosen by sweep; an aggressive 0.11 factor runaway-collapsed the world to ~1k.
  Removes the now-dead `ChronicleRules` and `RegionRules.forcedCollapse*` config.
- **Navbar splits primary surfaces from account controls.** The eleven top-level
  links sat in one undifferentiated row. Auth, Admin and Guide are now icon-only and
  grouped to the right behind a divider, so the primary surfaces (Chronicle … Species)
  read as one cluster and the utility controls as another. Labels move to `title` +
  `aria-label`, so nothing is lost to assistive tech.

### Fixed

- **The home hero's live map rendered at zero height.** `MiniUniverseMap` never gave
  `.universe-grid` a layout, and `.region-cell` is globally `position: absolute` (the
  universe page's hex map places each cell itself) — so all 108 cells collapsed to a
  0px-tall stack and the hero's entire right half read as empty. The mini-map now lays
  its cells out on a real 12-wide lattice, each washed by its region's life/energy, so
  the hero is anchored by the field it was always meant to show. The hex map is
  untouched (the fix is scoped to `.map-shell`).
- **"Active Lineages" listed extinct species.** The home strip sorted every species
  alphabetically and took the first eight — extinct included, and never by prominence —
  so dead lineages surfaced under an "Active" heading. It now excludes extinct species
  and leads with the largest by population.
- **Species and region event timelines ran the page for thousands of pixels.** Both
  rendered every bundled event full-height (the species page reached ~16,000px). A
  shared `EventTimeline` now shows eight with a "Show all N events" reveal and clamps
  each card's summary to two lines.

- **Population growth was rectified downward by integer truncation.** `int(N(1+g))`
  floors, and flooring is a rectifier at small `N`: it erased every positive tick whose
  gain was under one whole individual (`N·g < 1`, i.e. `N < ~167` at the median
  `g=0.006`) while rounding every loss down to a full individual — a small population
  could only fall, never climb, no matter how good its habitat. It is now
  deterministic **stochastic rounding** (fractional part = probability of rounding up),
  restoring `E[N'] = N(1+g)`. Measured: total population **+49%** (62,214 → 92,737 at 20k
  before the collapse change), and populations stop ratcheting to 1. Replay-identical.
- **Delta rows read as absolute counts.** The Distribution/Life Field drift row and
  the Dynamic Report metric cards show a *change* over the report window, but
  `formatDelta` dropped the sign at zero — so an extinct species whose population
  held steady rendered "Population 0" next to a header reading "12 population", as if
  the two disagreed. The sign is now derived from the rounded magnitude and a
  no-change reads "±0" / "±0pp" / "±0 pts", unmistakably a delta rather than a count.
- **Phylogenetic tree labels collided.** `buildPhylogeny` centred each parent on its
  children (`(min+max)/2`), so a single-child parent landed on its child's exact row —
  two lifelines shared one `y` and their name labels rendered on top of each other
  ("OLOS" over "THERA-21", "KARST-3" over "SOLEN-65"). Every node now takes its own
  row in DFS pre-order, so each lineage is its own horizontal line.
- **Status-strip tooltips were clipped into a broken block.** `.status-band { overflow:
  hidden }` — present to trim the cell backgrounds to the band's rounded corners — also
  sliced the InfoTip bubbles that pop above the top row, so the Alpha Age tip read as a
  cut-off dark rectangle. The end cells are now rounded to the band directly (in both
  the 5-column and 2-column layouts) and the clip is gone.
- **Region page over-ran and mis-stacked.** The Region Events timeline rendered every
  bundled event full-height (~25 cards, ~4000px); it now shows 8 with a "Show all N
  events" reveal and clamps each summary to two lines. Population Composition stretched
  its few bars to match the taller Related Species column, pinning them to the bottom
  under a large empty gap; the grid now aligns to the start. The Life Field's
  centred-square canvas left wide inert bands on its 16/9 shell; the shell is now 4/3,
  cutting the dead width from ~44% to ~25%.
- **Snapshot frame budget — the unbounded per-tick write.** `save_alpha` wrote a
  full snapshot set on every tick (~844 rows at Alpha's size, ~36M rows/day at the
  default 2s tick) with no retention. A production database reached ~64.7M
  snapshot rows over ~93k ticks and ~20 GB — >99% of its contents — while the
  event log it was tuned around sat at 13.8k rows. Frames are now kept on a
  derived stride (`tick % stride == 0`, stride the smallest power of two fitting
  history into `EVOVERSE_SNAPSHOT_FRAME_BUDGET`), with a batched, idempotent
  `compact_snapshots` sweep in the worker loop that both maintains a live universe
  and drains a pre-stride backlog. Size is now flat forever (~840k rows at the
  shipped budget) and history keeps its full span, losing only resolution.
  Migration `012_snapshot_frame_budget.sql` indexes the frame scan. See
  [`docs/PERFORMANCE_LOOP.md`](docs/PERFORMANCE_LOOP.md).
- **Deep history was unreachable.** `/universes/alpha/snapshots` capped a page at
  100 and `/universe` requested exactly that, so the time scrubber only ever saw
  the newest 100 ticks — a few minutes of a universe millions of ticks old,
  regardless of how much history was stored. The cap is now the frame budget, and
  `/universe` asks for the whole timeline.
- **Observability writes no longer stall the simulation.** `record_api_request`,
  `record_api_error` and `track_product_event` took the same lock the engine holds
  while advancing a tick, and the admin dashboard held it across whole-table log
  aggregates. Log writes now use a dedicated lock (the DB serialises the
  repository path on its own), the summary holds the state lock only for the
  universe block, and the middleware hands its synchronous insert to a worker
  thread instead of blocking the event loop.

### Added

- **`/science` — does Alpha flock?** A public page carrying the scale-free
  correlation measurement from Cavagna et al. (starling flocks, PNAS 2010) applied
  to Alpha, backed by a new `/universes/alpha/diagnostics` endpoint. Prose lives in
  `content/science.md` like the other info pages; `CriticalityPanel` renders the
  reach curves, the size scan, patch sizes and the census. Every panel states the
  evidence it stands on, draws the reach curve faint past the point where too few
  region pairs remain to average, and leaves a slot visibly blank — not greyed —
  where the evidence cannot carry a number. The trigger support gate lives in the
  API (`MIN_TRIGGER_SUPPORT`), not the view, so no consumer can print singleton
  lift by accident. Vocabulary on the page is deliberately ours ("reach",
  "flocking", "patches"); the FAQ maps each one to its name in the literature.
- **Worker-measured scale-free scan.** The scan replays four lattice sizes from
  seed and costs ~20s against ~8ms for every other diagnostic, so it cannot ride a
  request. The worker measures it on a timer and upserts into `diagnostics_runs`
  (migration `013`), keyed on `(universe_id, kind)` so it holds one row and cannot
  grow. The API serves it as a dated measurement; `null` renders as a blank rather
  than a verdict.
- **`population` report scope in the UI.** `/reports?scope=population` — a single
  species' colony within a single region, the one view of a colony's own
  trajectory — was implemented end to end (backend metrics, frontend labels,
  formats and colors) but never wired into the scope dropdown. Added the option.

- **Keyset (cursor) pagination for event feeds.** The chronicle, region, and
  species event feeds now page straight from the DB via a `(tick, id)` keyset
  instead of the in-memory (tail-capped) list, so they scroll arbitrarily deep
  (years of history) at constant per-page cost. New `AlphaStateRepository.events_page`,
  optional `cursor` on the `chronicle` / `region_events` / `species_events` store
  methods and their endpoints, and a `pagination.nextCursor` field added alongside
  the existing `hasMore` / `nextOffset` / `total` (additive — offset clients keep
  working). Backed by `(region_id, tick, id)` / `(species_id, tick, id)` indexes
  (`migrations/011_event_feed_keyset_indexes.sql`). Table partitioning for
  millions-of-rows scale is deferred to the backlog. See
  [`docs/PERFORMANCE_LOOP.md`](docs/PERFORMANCE_LOOP.md).
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
  **(C)** conditional triggers, per-motif-family lift tables (spatial / morphotype /
  lineage) joining each motif to the state (era, region bands, collapse, chirality,
  catalyst) it forms under — statically (spatial on region conditions, morphotype and
  lineage on origin-region conditions) and in deterministic-replay trace mode, where
  `SPECIES_EMERGED` events are joined to their origin region's condition at emergence.
  New benchmark flags `--correlation --patterns --triggers --scale-free
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
- **Two-tier Era gate — eras are now earned, not seeded** (design §6.4). The
  universe advances Expansion → **Stabilization** once its `homochirality_index`
  crosses `life_gate_index` (chemistry → life), and Stabilization → **Intelligence**
  once it crosses `mind_gate_index` *and* a lineage has `mind_locked` (life → mind).
  Because no lineage locks a mind until the cognitive tier (T2) ships, Intelligence
  stays genuinely unreachable for now. Progression is monotonic (an era is never
  lost) and announced once via a new `ERA_ADVANCED` chronicle event. New editable
  `ChiralityRules` knobs `lifeGateIndex`/`mindGateIndex`; `current_era` was already
  persisted, so no migration was needed. Covered by `backend/tests/test_chirality.py`.
  Featured-event and pagination consumers already tolerate the universe-scope events
  (`era_advanced`, universe `symmetry_break`) that carry no `regionId`.

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
