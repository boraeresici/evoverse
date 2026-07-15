-- Chirality field (T1): molecular symmetry breaking.
-- See docs/CHIRALITY_AND_MIND.md. Adds the current-state columns the API reads;
-- historical ee is carried in the existing universe_snapshots / region_snapshots
-- JSON payloads, so no snapshot-table schema change is needed here.

ALTER TABLE universes
  ADD COLUMN IF NOT EXISTS chirality_ee NUMERIC(6, 4) NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS homochirality_index NUMERIC(6, 4) NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS chirality_locked BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE regions
  ADD COLUMN IF NOT EXISTS chirality_ee NUMERIC(6, 4) NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS chirality_locked BOOLEAN NOT NULL DEFAULT FALSE;
