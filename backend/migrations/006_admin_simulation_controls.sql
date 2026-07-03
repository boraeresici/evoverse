CREATE TABLE IF NOT EXISTS admin_simulation_runs (
  id TEXT PRIMARY KEY,
  universe_id TEXT NOT NULL REFERENCES universes(id),
  action_type TEXT NOT NULL,
  status TEXT NOT NULL,
  actor_id TEXT NOT NULL,
  reason TEXT,
  requested_ticks INTEGER NOT NULL DEFAULT 0,
  applied_ticks INTEGER NOT NULL DEFAULT 0,
  seed INTEGER NOT NULL,
  before_tick BIGINT NOT NULL,
  after_tick BIGINT NOT NULL,
  before_world_age BIGINT NOT NULL,
  after_world_age BIGINT NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_admin_simulation_runs_universe
  ON admin_simulation_runs(universe_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_admin_simulation_runs_actor
  ON admin_simulation_runs(actor_id, created_at DESC);
