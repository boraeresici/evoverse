-- Keyset-pagination indexes for the per-entity event feeds.
--
-- The chronicle feed keysets on (universe_id, tick, id) — already covered by
-- migration 009. The region and species feeds keyset on the same (tick, id)
-- total order but filtered by region_id / species_id, so they need matching
-- composite indexes; otherwise each deep page filters by entity and then sorts
-- the whole subset in memory. The existing idx_events_{region,species}_age
-- indexes sort by world_age, which does not serve the (tick, id) order.

CREATE INDEX IF NOT EXISTS idx_events_region_tick
  ON events(region_id, tick, id);

CREATE INDEX IF NOT EXISTS idx_events_species_tick
  ON events(species_id, tick, id);
