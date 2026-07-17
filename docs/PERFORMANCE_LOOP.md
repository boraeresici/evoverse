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

## Snapshots — the actual disk driver

Everything above is about `events`, and it worked: the event log settles around
~14k rows. That made this document a blind spot. While it optimised a table that
was never large, `save_alpha` was writing an unbounded per-tick snapshot on every
call, and nothing here mentioned it.

`_insert_snapshot` wrote one `universe_snapshots` row plus one row per region, per
species and per population — **~844 rows per tick** at Alpha's size — with no
retention at all. At the default 2s tick that is ~36M rows/day. A production
database reached **~64.7M snapshot rows across ~93k ticks (about two days) and
~20 GB**, against 13.8k events and 402 `api_request_logs` rows. Snapshots were
>99% of the database.

It also drove the freeze, which looked like a locking bug and was not one: the
per-tick write happens under the simulation lock, and `EVOVERSE_API_REFRESH_ON_READ`
(default on) makes every API read take that same lock, so each request waited on a
844-row insert into 64M-row indexed tables.

The reader is what makes this absurd: those rows exist only for
`/universes/alpha/snapshots/{tick}/details`, which serves the `/universe` time
scrubber. The scrubber shows one frame at a time and a screen can address ~1500 of
them. The API's page cap was 100. So the write path produced tick-level resolution
that no reader could ever request.

### Frame budget

A **frame** is one snapshot set at a single tick. Frames are kept on a stride:

    stride = smallest 2^k such that (newest_tick / stride) <= SNAPSHOT_FRAME_BUDGET
    a frame exists  ⟺  tick % stride == 0

Stride is derived from the newest tick, never stored, so the write path and the
compaction job cannot disagree about which ticks are frames. It only ever doubles,
which means every tick kept at stride 2N was already a frame at stride N —
widening drops frames without shifting the surviving grid.

| # | Fix | Where | Effect |
|---|-----|-------|--------|
| 1 | **Stride the write** | `_insert_snapshot` | Skips ticks off the current stride. Reads the stride from the newest *stored* tick, so a save cannot widen the stride and skip its own frame. |
| 2 | **Compaction** | `compact_snapshots` → worker loop | Deletes off-stride frames, batched (`SNAPSHOT_COMPACT_BATCH` frames/call). Idempotent, so the same call maintains a live universe and drains a pre-stride backlog. Doomed ticks come from the small `universe_snapshots`; detail rows go by `(universe_id, tick, ...)` primary key. |
| 3 | **Uncap the reader** | [`main.py`](../backend/app/main.py) `get_alpha_snapshots` | Page cap goes from a flat 100 to the frame budget, so a client can ask for the entire timeline. `/universe` now does. |
| 4 | **Compaction index** | [`migrations/012_snapshot_frame_budget.sql`](../backend/migrations/012_snapshot_frame_budget.sql) | `universe_snapshots(universe_id, tick)` backs the frame scan; `tick % stride <> 0` cannot use an index, so it is kept on the smallest table. |

History keeps its full span and gives up only resolution — the axis the scrubber
cannot render anyway. Recent fidelity is unaffected: the live view reads current
state, not snapshots.

If compaction never runs, the write path alone still bounds frames at
`budget * log2(ticks/budget)` rather than growing linearly. Compaction closes the
gap to the budget.

End-to-end check: 1600 ticks at `budget=50` held the frame count at 31–50 (the
designed `budget/2 .. budget` oscillation) while the stored frames still spanned
96–98% of all ticks, and the oldest surviving frame resolved to full detail. Disk
projection at the shipped `budget=2000`: ~840k rows (~250 MB), flat forever,
against ~13.3 billion rows/year unbounded.

| Env | Default | Meaning |
|-----|---------|---------|
| `EVOVERSE_SNAPSHOT_FRAME_BUDGET` | `2000` | Frames kept for all of world history. Also the `/snapshots` page cap. |
| `EVOVERSE_SNAPSHOT_COMPACT_BATCH` | `200` | Frames dropped per compaction call. |
| `EVOVERSE_WORKER_COMPACT_EVERY_STEPS` | `30` | Worker steps between compaction sweeps. `0` disables. |

## Diagnostics — one call that cannot be live

`/universes/alpha/diagnostics` backs `/science`. Its live probes read current
state and are cheap; the scale-free scan is not, and the gap is three orders of
magnitude:

| Call | Cost | Where it runs |
|------|------|---------------|
| `correlation_length` | 4.3 ms | per request |
| `pattern_census` | 0.6 ms | per request |
| `pattern_triggers` | 2.9 ms | per request |
| **`scale_free_scan`** | **19 734 ms** | worker only |

The scan re-seeds and replays the universe at four lattice sizes to ask whether ξ
grows with L — the decisive criticality test. At ~20s of CPU it cannot be attached
to a request: one page view would hold a worker for twenty seconds, and any
concurrency would bury the box.

So the worker runs it on a timer (`EVOVERSE_WORKER_SCAN_EVERY_STEPS`, ~2h at the
default step) and upserts the result into `diagnostics_runs`. The API serves the
cheap probes live and this row as a dated measurement, carrying the tick it was
taken at. `scaleFree: null` is a real state — a universe nobody has scanned yet
has no verdict, and the page renders the blank rather than implying one.

`diagnostics_runs` is keyed on `(universe_id, kind)` and upserted, so it holds one
row per diagnostic and cannot grow. Both other table families in this schema —
logs and snapshots — were append-only with no retention and had to be bounded
after they had already filled a disk. This one is bounded by its primary key from
the start.

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

Disk over time (default unlimited retention): **~0.39 events/tick** × 1 tick/2s ≈
**~17k events/day ≈ ~6.2M/year**; with the index this stays fast, but set
`EVOVERSE_MAX_STORED_EVENTS` if you want a hard disk bound.

> **This figure moved 2.5× and the reason is worth knowing.** It read ~0.15
> events/tick (~2.4M/year) when the chronicle was 1,571 events per 10,000 ticks and
> 91% of them were three scripted beats. Fixing the reporting resolution —
> resource shifts and declines are now measured against what was last reported
> rather than against the previous tick — did not add noise; it stopped the engine
> ignoring real movement it could not see. The chronicle is now 3,911 events per
> 10,000 ticks and 98% of them are the world's own. See
> [`SIMULATION_FLOW_AND_FORMULAS.md` §8](SIMULATION_FLOW_AND_FORMULAS.md).
>
> Two consequences for whoever plans capacity: the **events-table partitioning**
> backlog item arrives ~2.5× sooner than the note assumed, and the honest lever on
> volume is now `resourceShiftThreshold` / `declinePopulationRatio` — they are
> *reporting* thresholds and touch no dynamics, so raising them costs truth, not
> behaviour. Re-derive the rate with `make benchmark` rather than trusting this
> line; it is a snapshot of one tuning.
