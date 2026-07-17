-- Local order and domain count (T1): the gap between "every region has picked
-- a hand" and "every region picked the same one". See docs/CHIRALITY_AND_MIND.md.
-- Adds the current-state columns the API reads; historical values ride the
-- existing universe_snapshots JSON payload, so no snapshot-table schema change
-- is needed here (same rationale as 008_chirality_field.sql).

ALTER TABLE universes
  ADD COLUMN IF NOT EXISTS local_order_index NUMERIC(6, 4) NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS domain_count INTEGER NOT NULL DEFAULT 0;
