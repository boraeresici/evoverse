CREATE TABLE IF NOT EXISTS api_request_logs (
  id TEXT PRIMARY KEY,
  method TEXT NOT NULL,
  path TEXT NOT NULL,
  route TEXT,
  status_code INTEGER NOT NULL,
  duration_ms NUMERIC(10, 3) NOT NULL,
  request_id TEXT,
  user_id TEXT,
  client_host TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_api_request_logs_created
  ON api_request_logs(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_api_request_logs_status
  ON api_request_logs(status_code, created_at DESC);

CREATE TABLE IF NOT EXISTS api_error_logs (
  id TEXT PRIMARY KEY,
  method TEXT NOT NULL,
  path TEXT NOT NULL,
  route TEXT,
  status_code INTEGER NOT NULL,
  error_code TEXT NOT NULL,
  message TEXT,
  request_id TEXT,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_api_error_logs_created
  ON api_error_logs(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_api_error_logs_status
  ON api_error_logs(status_code, created_at DESC);

CREATE TABLE IF NOT EXISTS worker_run_events (
  id TEXT PRIMARY KEY,
  worker_id TEXT NOT NULL,
  universe_id TEXT NOT NULL REFERENCES universes(id),
  event_type TEXT NOT NULL,
  status TEXT NOT NULL,
  last_tick BIGINT NOT NULL DEFAULT 0,
  last_world_age BIGINT NOT NULL DEFAULT 0,
  last_step BIGINT NOT NULL DEFAULT 0,
  error TEXT,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_worker_run_events_worker
  ON worker_run_events(worker_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_worker_run_events_type
  ON worker_run_events(universe_id, event_type, created_at DESC);

CREATE TABLE IF NOT EXISTS product_analytics_events (
  id TEXT PRIMARY KEY,
  universe_id TEXT NOT NULL REFERENCES universes(id),
  event_name TEXT NOT NULL,
  user_id TEXT,
  session_id TEXT,
  subject_type TEXT,
  subject_id TEXT,
  source TEXT NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_product_analytics_events_name
  ON product_analytics_events(universe_id, event_name, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_product_analytics_events_subject
  ON product_analytics_events(subject_type, subject_id, created_at DESC);
