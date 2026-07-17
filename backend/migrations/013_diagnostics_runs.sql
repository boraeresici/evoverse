-- Store the latest result of each expensive diagnostic.
--
-- The scale-free scan re-seeds and replays the universe at four lattice sizes to
-- ask whether the correlation length grows with the world. That is the decisive
-- criticality test, and it takes ~20s of CPU — three orders of magnitude past the
-- ~8ms the live diagnostics (C(r), census, triggers) cost against current state.
-- It cannot run per request: a page view would hold a worker for 20 seconds and
-- any concurrency would bury the box.
--
-- So the worker runs it on a timer and parks the result here, and the API serves
-- the cheap parts live and this row as a dated measurement — which is how the
-- claim honestly reads anyway: you ran the experiment at a tick, you report what
-- it said at that tick.
--
-- Keyed on (universe_id, kind) and upserted, so it holds exactly one row per
-- diagnostic and cannot grow. Snapshot and log tables in this schema were both
-- append-only with no retention and both had to be bounded after the fact; this
-- one is bounded by its primary key from the start. A verdict-over-time history
-- would be a deliberate addition, not a side effect of writing.

CREATE TABLE IF NOT EXISTS diagnostics_runs (
  universe_id TEXT NOT NULL REFERENCES universes(id),
  kind TEXT NOT NULL,
  seed INTEGER NOT NULL,
  ticks BIGINT NOT NULL,
  verdict TEXT NOT NULL,
  duration_ms NUMERIC(10, 3) NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  measured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (universe_id, kind)
);
