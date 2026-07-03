CREATE TABLE IF NOT EXISTS simulation_rule_configs (
  id TEXT PRIMARY KEY,
  universe_id TEXT NOT NULL,
  revision INTEGER NOT NULL,
  rules_hash TEXT NOT NULL,
  rules JSONB NOT NULL,
  applied_by TEXT NOT NULL,
  reason TEXT,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_simulation_rule_configs_active
  ON simulation_rule_configs(universe_id, is_active, revision DESC);

CREATE INDEX IF NOT EXISTS idx_simulation_rule_configs_revision
  ON simulation_rule_configs(universe_id, revision DESC);

CREATE TABLE IF NOT EXISTS simulation_rule_audit_logs (
  id TEXT PRIMARY KEY,
  universe_id TEXT NOT NULL,
  action_type TEXT NOT NULL,
  status TEXT NOT NULL,
  actor_id TEXT NOT NULL,
  reason TEXT,
  current_rules_hash TEXT,
  candidate_rules_hash TEXT,
  target_revision INTEGER,
  validation_errors JSONB NOT NULL DEFAULT '[]'::jsonb,
  reload_strategy JSONB NOT NULL DEFAULT '{}'::jsonb,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_simulation_rule_audit_logs_universe
  ON simulation_rule_audit_logs(universe_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_simulation_rule_audit_logs_action
  ON simulation_rule_audit_logs(action_type, status, created_at DESC);
