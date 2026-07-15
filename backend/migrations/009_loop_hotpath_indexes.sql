-- Worker-loop hot-path indexes. See docs/PERFORMANCE_LOOP.md.
--
-- The worker reloads and persists state on every tick. Those queries filter/sort
-- events by (universe_id, tick, id) and delete/reload catalyst_actions by
-- universe_id, but no index covered either access pattern, so both degraded into
-- full scans as the tables grew. These indexes keep the loop cost flat:
--
--   * events(universe_id, tick, id) backs the tail load (ORDER BY tick DESC,
--     id DESC LIMIT N), the append watermark (MAX(tick) / tick >= cutoff), and
--     optional retention pruning.
--   * catalyst_actions(universe_id) backs the per-save delete + reload.

CREATE INDEX IF NOT EXISTS idx_events_universe_tick
  ON events(universe_id, tick, id);

CREATE INDEX IF NOT EXISTS idx_catalyst_actions_universe
  ON catalyst_actions(universe_id);
