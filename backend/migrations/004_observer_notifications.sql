CREATE TABLE IF NOT EXISTS observer_follows (
  id TEXT PRIMARY KEY,
  universe_id TEXT NOT NULL REFERENCES universes(id),
  user_id TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_observer_follows_entity UNIQUE (universe_id, user_id, entity_type, entity_id)
);

CREATE INDEX IF NOT EXISTS idx_observer_follows_user
  ON observer_follows(universe_id, user_id, entity_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_observer_follows_entity
  ON observer_follows(entity_type, entity_id, created_at DESC);

CREATE TABLE IF NOT EXISTS notification_reads (
  universe_id TEXT NOT NULL REFERENCES universes(id),
  user_id TEXT NOT NULL,
  notification_id TEXT NOT NULL,
  read_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, notification_id)
);

CREATE INDEX IF NOT EXISTS idx_notification_reads_user
  ON notification_reads(universe_id, user_id, read_at DESC);
