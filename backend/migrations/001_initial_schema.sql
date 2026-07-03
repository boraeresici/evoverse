CREATE TABLE IF NOT EXISTS universes (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  age_years BIGINT NOT NULL,
  current_era TEXT NOT NULL,
  tick BIGINT NOT NULL,
  stability_index NUMERIC(6, 3) NOT NULL
);

CREATE TABLE IF NOT EXISTS regions (
  id TEXT PRIMARY KEY,
  universe_id TEXT NOT NULL REFERENCES universes(id),
  x INTEGER NOT NULL,
  y INTEGER NOT NULL,
  biome_type TEXT NOT NULL,
  energy_level NUMERIC(6, 3) NOT NULL,
  resource_density NUMERIC(6, 3) NOT NULL,
  stability NUMERIC(6, 3) NOT NULL,
  dominant_species_id TEXT,
  collapsed BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS species (
  id TEXT PRIMARY KEY,
  universe_id TEXT NOT NULL REFERENCES universes(id),
  name TEXT NOT NULL,
  origin_region_id TEXT NOT NULL REFERENCES regions(id),
  emerged_at_world_age BIGINT NOT NULL,
  status TEXT NOT NULL,
  generation INTEGER NOT NULL,
  parent_species_id TEXT REFERENCES species(id),
  traits JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS populations (
  species_id TEXT NOT NULL REFERENCES species(id),
  region_id TEXT NOT NULL REFERENCES regions(id),
  population_count BIGINT NOT NULL,
  energy_consumption NUMERIC(8, 4) NOT NULL,
  growth_rate NUMERIC(8, 4) NOT NULL,
  migration_pressure NUMERIC(8, 4) NOT NULL,
  last_updated_tick BIGINT NOT NULL,
  PRIMARY KEY (species_id, region_id)
);

CREATE TABLE IF NOT EXISTS events (
  id TEXT PRIMARY KEY,
  universe_id TEXT NOT NULL REFERENCES universes(id),
  region_id TEXT REFERENCES regions(id),
  species_id TEXT REFERENCES species(id),
  event_type TEXT NOT NULL,
  severity INTEGER NOT NULL,
  world_age BIGINT NOT NULL,
  tick BIGINT NOT NULL,
  title TEXT NOT NULL,
  summary TEXT NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_events_universe_age ON events(universe_id, world_age DESC);
CREATE INDEX IF NOT EXISTS idx_events_region_age ON events(region_id, world_age DESC);
CREATE INDEX IF NOT EXISTS idx_events_species_age ON events(species_id, world_age DESC);

CREATE TABLE IF NOT EXISTS catalyst_actions (
  id TEXT PRIMARY KEY,
  universe_id TEXT NOT NULL REFERENCES universes(id),
  region_id TEXT NOT NULL REFERENCES regions(id),
  action_type TEXT NOT NULL,
  user_id TEXT NOT NULL,
  created_at_tick BIGINT NOT NULL,
  expires_at_tick BIGINT NOT NULL,
  strength NUMERIC(6, 3) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS catalyst_action_logs (
  id TEXT PRIMARY KEY,
  universe_id TEXT NOT NULL REFERENCES universes(id),
  region_id TEXT NOT NULL REFERENCES regions(id),
  action_type TEXT NOT NULL,
  user_id TEXT NOT NULL,
  day_key TEXT NOT NULL,
  created_at_tick BIGINT NOT NULL,
  world_age BIGINT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_catalyst_action_logs_user_day ON catalyst_action_logs(user_id, action_type, day_key);
CREATE INDEX IF NOT EXISTS idx_catalyst_action_logs_region_tick ON catalyst_action_logs(region_id, created_at_tick DESC);

CREATE TABLE IF NOT EXISTS universe_snapshots (
  universe_id TEXT NOT NULL REFERENCES universes(id),
  tick BIGINT NOT NULL,
  world_age BIGINT NOT NULL,
  region_count INTEGER NOT NULL,
  species_count INTEGER NOT NULL,
  population_count BIGINT NOT NULL,
  event_count BIGINT NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (universe_id, tick)
);

CREATE INDEX IF NOT EXISTS idx_universe_snapshots_age ON universe_snapshots(universe_id, world_age DESC);

CREATE TABLE IF NOT EXISTS worker_heartbeats (
  worker_id TEXT PRIMARY KEY,
  universe_id TEXT NOT NULL REFERENCES universes(id),
  status TEXT NOT NULL,
  last_tick BIGINT NOT NULL,
  last_world_age BIGINT NOT NULL,
  last_step BIGINT NOT NULL,
  last_error TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_worker_heartbeats_universe ON worker_heartbeats(universe_id, updated_at DESC);
