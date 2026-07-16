-- Index the snapshot compaction path.
--
-- Migration 003 added four per-tick snapshot tables. `save_alpha` wrote one
-- universe row plus one row per region, per species and per population on *every*
-- tick, and nothing ever pruned them, so they grew at ~844 rows/tick (~36M
-- rows/day at the default 2s tick) and reached ~64.7M rows -- the bulk of the
-- database. Meanwhile the only consumer, the /universe time scrubber, can address
-- at most 100 frames, and the API caps a page at 100.
--
-- Snapshots are now kept on a stride: a frame exists only where
-- `tick % stride == 0`, with stride the smallest power of two that fits history
-- into EVOVERSE_SNAPSHOT_FRAME_BUDGET. History keeps its full span and gives up
-- only resolution, which is the axis the scrubber cannot render anyway. Recent
-- fidelity is unaffected -- the live view reads current state, not snapshots.
--
-- Compaction picks doomed ticks out of universe_snapshots (small, bounded by the
-- budget) and deletes matching rows from the detail tables by tick, which their
-- (universe_id, tick, ...) primary keys already serve. This index is for the
-- frame scan itself: the `tick % stride <> 0` predicate cannot use an index, so
-- the scan is bounded by keeping it on the smallest table.

CREATE INDEX IF NOT EXISTS idx_universe_snapshots_universe_tick
  ON universe_snapshots(universe_id, tick);
