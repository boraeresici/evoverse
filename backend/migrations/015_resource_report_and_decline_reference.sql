-- Resource-shift reporting and decline high-water mark (T1 plumbing): the anchor
-- values a resource-shift event is measured away from, and the peak a population
-- decline is measured down from. See app/domain/models.py Region and Population
-- for the semantics. Adds the current-state columns the engine reads and writes;
-- historical values ride the existing region_snapshots / population_snapshots
-- JSON payload columns, so no snapshot-table schema change is needed here (same
-- rationale as 014_local_order_and_domain_count.sql).

ALTER TABLE regions
  ADD COLUMN IF NOT EXISTS last_reported_resource_density NUMERIC(6, 3) NOT NULL DEFAULT 0;

ALTER TABLE populations
  ADD COLUMN IF NOT EXISTS decline_reference_population INTEGER NOT NULL DEFAULT 0;
