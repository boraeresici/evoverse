# Simulation Loop Performance & Server Sizing

This note explains why a long-running deployment used to slow down and eventually
error out, what changed to keep the worker loop flat over time, and how to size a
server for it.

## Symptom

On a server the app "kept throwing errors and freezing." The simulation itself is
light (pure-Python aggregate math, ~700 ticks/sec on a laptop; the worker only
advances **1 tick every 2 seconds**), so this was never a CPU-shortage problem.
It was **unbounded growth in the persistence hot path**.

## Root cause

Every worker step runs `AlphaStore.advance()` →
[`load_alpha`](../backend/app/persistence/repository.py) then
[`save_alpha`](../backend/app/persistence/repository.py). Two things grew without
bound as the event log accumulated:

1. **Full-history reload.** `load_alpha` hydrated the *entire* event table into
   memory on every reload (which happens each worker tick and, with
   `refresh_on_read`, each API read). Cost grew linearly with total events.
2. **Whole-log dedup on write.** `save_alpha` built an
   `id IN (<every event id ever created>)` clause on every save to find which
   events were new. Beyond ~65k events this exceeds the driver's bind-parameter
   limit → **constant errors**; well before that each save gets progressively
   slower → **freezing**.

Nothing pruned the event log, so both effects compounded forever. A bigger server
only delays the wall — it does not remove it.

## The fixes

| # | Fix | Where | Effect |
|---|-----|-------|--------|
| 1 | **Tail-load events** | `load_alpha` | Hydrates only the newest `MAX_LOADED_EVENTS` into memory; reload cost is now O(slice), not O(history). `next_event_index` stays correct because the newest ids carry the highest suffix. |
| 2 | **Append watermark** | `save_alpha` → `_unpersisted_events` | Replaces the whole-log `IN (...)` with a `MAX(tick)`-bounded lookup. The event store is append-only, so any unpersisted event sits at/after the newest stored tick; dedup now touches one tick's worth of ids. Removes the parameter-limit crash and makes save O(new events). |
| 3 | **Optional DB retention** | `save_alpha` → `_prune_events` | With `MAX_STORED_EVENTS > 0`, prunes the oldest rows on write to bound on-disk growth. Only oldest rows are removed, so the append/tail boundary is never touched. Default `0` = keep everything (unchanged behavior). |
| 4 | **Hot-path indexes** | [`migrations/009_loop_hotpath_indexes.sql`](../backend/migrations/009_loop_hotpath_indexes.sql) | `events(universe_id, tick, id)` backs the tail load, watermark, and pruning; `catalyst_actions(universe_id)` backs the per-save delete + reload. Previously both were full scans. |

End-to-end check: 600 loop steps with tight caps kept memory and DB event counts
under their caps and per-step time flat (no growth), with `next_event_index`
preserved across tail-loads and pruning.

### Why `populations` was **not** switched to a partial write

An earlier plan was to stop the per-step delete+reinsert of `populations` in favor
of writing only changed rows. On inspection this is **unsafe and not a win**:

- The migration path increments an existing population's count **without** bumping
  `last_updated_tick` ([`engine.py`](../backend/app/simulation/engine.py) —
  `_migrate_population`), so a "changed rows only" write keyed on that field would
  silently drop updates (data drift).
- Nearly every population's `growth_rate`/count changes **every** tick, so a partial
  write would rewrite almost all rows anyway — no churn saved.

The current bounded delete + bulk-insert (two statements over a set that is capped
by species × regions, not by time) is correct and effectively optimal. It was left
as-is deliberately.

## Configuration knobs

Environment variables (read at import in `repository.py`):

| Variable | Default | Meaning |
|----------|---------|---------|
| `EVOVERSE_MAX_LOADED_EVENTS` | `2000` | How many recent events are hydrated into memory per reload. Higher = deeper in-memory feed but heavier reloads. |
| `EVOVERSE_MAX_STORED_EVENTS` | `0` (unlimited) | DB retention cap. Set e.g. `100000` to bound disk. Keep `>= MAX_LOADED_EVENTS`. |

Existing loop knobs for reference (see [`config.py`](../backend/app/config.py)):
`EVOVERSE_WORKER_INTERVAL_SECONDS` (default `2`),
`EVOVERSE_WORKER_TICKS_PER_STEP` (default `1`).

## Deep event feeds — keyset pagination

The in-memory working set is bounded by `MAX_LOADED_EVENTS`, so event feeds do
**not** page over that in-memory slice. Instead they page straight from the DB via
keyset (cursor) pagination, so the chronicle / region / species feeds scroll
arbitrarily deep (years of history) at constant per-page cost — without inflating
the cap.

- **Repository** — `AlphaStateRepository.events_page(...)` orders newest-first by
  the `(tick, id)` total order. A `cursor` resumes with `WHERE (tick, id) <
  (cursor)` (O(log n) per page via the `idx_events_*_tick` indexes); with no
  cursor it falls back to `OFFSET` so the legacy offset contract still works to any
  depth (just slower deep). Cursors are opaque `"{tick}:{id}"` strings
  (`encode_event_cursor` / `decode_event_cursor`).
- **Store** — `chronicle` / `region_events` / `species_events` take an optional
  `cursor` and route to the DB when persistence is on; memory mode pages over the
  in-memory window (all the history that mode has).
- **API** — those three endpoints accept a `cursor` query param and return
  `pagination.nextCursor` alongside the existing `hasMore` / `nextOffset` / `total`
  (additive, so existing offset clients keep working).
- **Indexes** — `migrations/011_event_feed_keyset_indexes.sql` adds
  `(region_id, tick, id)` and `(species_id, tick, id)`; the chronicle uses the
  `(universe_id, tick, id)` index from migration 009.

Prefer `cursor` for deep scroll (constant cost); `offset` remains for shallow
jumps. `MAX_LOADED_EVENTS` now only governs the worker/API reload cost, not feed
depth.

### Backlog — table partitioning

`events_page` keeps a single growing table fast via indexes. When the table nears
millions of rows (a few years), switch `events` to monthly range partitions on
`tick`/`created_at`: per-partition indexes stay small, retention becomes `DROP
PARTITION` instead of `DELETE`, and cold partitions can be archived (Parquet/JSONL).
Deferred until real volume — tracked in `sira.md` (Paket 17).

## Server sizing

With the loop flat, requirements are modest.

| Scenario | vCPU | RAM | Disk | Notes |
|----------|------|-----|------|-------|
| Runtime minimum (sim + API + Postgres) | 1 | 2 GB | 20 GB SSD | The app genuinely runs in this. |
| **Recommended for Coolify** | **2** | **4 GB** | 40–80 GB SSD | The real constraint is the **Next.js build** (~1.5–2 GB); a 1 GB box OOMs at build and the deploy appears to "hang". |

Disk over time (default unlimited retention): ~0.15 events/tick × 1 tick/2s ≈
~6.5k events/day ≈ ~2.4M/year; with the index this stays fast, but set
`EVOVERSE_MAX_STORED_EVENTS` if you want a hard disk bound.
