# Snapshot Strategy

Alpha keeps two snapshot layers:

- `universe_snapshots`: compact tick summary for list, latest, and coarse Time Zoom navigation.
- Entity detail snapshots: `region_snapshots`, `species_snapshots`, and `population_snapshots` for report, comparison, Replay Lite, and detailed Time Zoom reads.

## Write Model

Every persisted Alpha save writes one summary snapshot and, when missing for that tick, one detail row per current region, species, and population edge. The event store remains append-only and separate from snapshots.

The detail tables are append-only per `(universe_id, tick, entity id)` key. Existing summary snapshots created before the detail schema are not backfilled automatically; new saves start producing detail coverage.

## Read Model

Existing summary APIs remain stable:

- `GET /universes/alpha/snapshots/latest`
- `GET /universes/alpha/snapshots?limit=50&offset=0`

Detailed reads use:

- `GET /universes/alpha/snapshots/{tick}/details`

The detail response contains:

- `snapshot`: the summary snapshot.
- `coverage`: counts for region, species, and population detail rows.
- `regions`: region metrics at that tick.
- `species`: species metrics at that tick.
- `populations`: species-region population edges at that tick.

## Product Use

Dynamic Report should compare metrics across summary snapshots first, then fetch detail snapshots only for selected ticks or selected entities. This keeps the default report light while preserving enough detail for charts, Replay Lite event markers, and region/species drilldowns.

## Time Navigation

The Universe page turns these snapshots into a scrubbable timeline (`UniverseTimeExplorer` + `TimeScrubber`):

- The page fetches the latest 100 summary snapshots server-side (`getSnapshots`) as scrubber frames (worldAge, populationCount, speciesCount, stability sparkline).
- Dragging the scrubber (or Play) selects a historical frame; the map redraws from that frame's detail snapshot. Region/species rows are mapped to the live `RegionSummary`/`SpeciesSummary` shape via `frontend/lib/timeline.ts`.
- Detail reads go through a same-origin BFF proxy — `GET /api/snapshots/{tick}/details` → backend `GET /universes/alpha/snapshots/{tick}/details` — because the backend CORS allowlist is intentionally narrow and the browser must not call the API cross-origin (consistent with the same-origin BFF direction). Frames are cached client-side by tick and fetches are debounced.
- Era bands (Genesis / Expansion / Stabilization / Intelligence) are derived client-side from world-age thresholds in `timeline.ts`. The backend `current_era` is currently static and the literal tick→calendar mapping is an open product decision, so the thresholds and the log-axis option are documented placeholders pending that decision.
- Time Zoom presets (Recent / Wider / Full) set the visible fraction of loaded frames; "Live" returns to the current state; cinematic Play steps through frames with CSS transitions on region cells.
