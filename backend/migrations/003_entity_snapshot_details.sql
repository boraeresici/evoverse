CREATE TABLE IF NOT EXISTS region_snapshots (
  universe_id TEXT NOT NULL REFERENCES universes(id),
  tick BIGINT NOT NULL,
  region_id TEXT NOT NULL REFERENCES regions(id),
  world_age BIGINT NOT NULL,
  x INTEGER NOT NULL,
  y INTEGER NOT NULL,
  biome_type TEXT NOT NULL,
  energy_level NUMERIC(6, 3) NOT NULL,
  resource_density NUMERIC(6, 3) NOT NULL,
  stability NUMERIC(6, 3) NOT NULL,
  dominant_species_id TEXT,
  collapsed BOOLEAN NOT NULL DEFAULT FALSE,
  population_count BIGINT NOT NULL,
  species_count INTEGER NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (universe_id, tick, region_id)
);

CREATE INDEX IF NOT EXISTS idx_region_snapshots_entity_age
  ON region_snapshots(region_id, world_age DESC);

CREATE INDEX IF NOT EXISTS idx_region_snapshots_universe_age
  ON region_snapshots(universe_id, world_age DESC);

CREATE TABLE IF NOT EXISTS species_snapshots (
  universe_id TEXT NOT NULL REFERENCES universes(id),
  tick BIGINT NOT NULL,
  species_id TEXT NOT NULL REFERENCES species(id),
  world_age BIGINT NOT NULL,
  name TEXT NOT NULL,
  status TEXT NOT NULL,
  origin_region_id TEXT NOT NULL REFERENCES regions(id),
  generation INTEGER NOT NULL,
  parent_species_id TEXT,
  population_count BIGINT NOT NULL,
  region_count INTEGER NOT NULL,
  traits JSONB NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (universe_id, tick, species_id)
);

CREATE INDEX IF NOT EXISTS idx_species_snapshots_entity_age
  ON species_snapshots(species_id, world_age DESC);

CREATE INDEX IF NOT EXISTS idx_species_snapshots_universe_age
  ON species_snapshots(universe_id, world_age DESC);

CREATE TABLE IF NOT EXISTS population_snapshots (
  universe_id TEXT NOT NULL REFERENCES universes(id),
  tick BIGINT NOT NULL,
  species_id TEXT NOT NULL REFERENCES species(id),
  region_id TEXT NOT NULL REFERENCES regions(id),
  world_age BIGINT NOT NULL,
  population_count BIGINT NOT NULL,
  energy_consumption NUMERIC(8, 4) NOT NULL,
  growth_rate NUMERIC(8, 4) NOT NULL,
  migration_pressure NUMERIC(8, 4) NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (universe_id, tick, species_id, region_id)
);

CREATE INDEX IF NOT EXISTS idx_population_snapshots_species_age
  ON population_snapshots(species_id, world_age DESC);

CREATE INDEX IF NOT EXISTS idx_population_snapshots_region_age
  ON population_snapshots(region_id, world_age DESC);

CREATE INDEX IF NOT EXISTS idx_population_snapshots_universe_age
  ON population_snapshots(universe_id, world_age DESC);
