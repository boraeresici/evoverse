# Changelog

All notable changes to Evoverse are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to
follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Active sprint tracking lives in `sıra.md`; `docs/` and `prd.md` are product references.

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
