CREATE TABLE IF NOT EXISTS catalyst_user_roles (
  universe_id TEXT NOT NULL REFERENCES universes(id),
  user_id TEXT NOT NULL,
  role TEXT NOT NULL,
  status TEXT NOT NULL,
  granted_by TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (universe_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_catalyst_user_roles_status
  ON catalyst_user_roles(universe_id, role, status);

CREATE INDEX IF NOT EXISTS idx_catalyst_action_logs_user
  ON catalyst_action_logs(universe_id, user_id, created_at_tick DESC);

CREATE INDEX IF NOT EXISTS idx_catalyst_action_logs_day
  ON catalyst_action_logs(universe_id, user_id, action_type, day_key);
