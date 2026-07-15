-- Chiral central dogma (T1, §6.2–6.3): a lineage's handedness and mismatch load.
-- See docs/CHIRALITY_AND_MIND.md. Adds the current-state columns the API reads;
-- historical values ride the existing species_snapshots JSON payload.

ALTER TABLE species
  ADD COLUMN IF NOT EXISTS chirality SMALLINT NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS heterochiral_load NUMERIC(6, 4) NOT NULL DEFAULT 0;
