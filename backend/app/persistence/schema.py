from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    MetaData,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)


metadata = MetaData()

schema_migrations = Table(
    "schema_migrations",
    metadata,
    Column("version", Text, primary_key=True),
    Column("name", Text, nullable=False),
    Column("checksum", Text, nullable=False),
    Column("applied_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)

universes = Table(
    "universes",
    metadata,
    Column("id", Text, primary_key=True),
    Column("name", Text, nullable=False),
    Column("age_years", BigInteger, nullable=False),
    Column("current_era", Text, nullable=False),
    Column("tick", BigInteger, nullable=False),
    Column("stability_index", Numeric(6, 3), nullable=False),
    Column("chirality_ee", Numeric(6, 4), nullable=False, default=0),
    Column("homochirality_index", Numeric(6, 4), nullable=False, default=0),
    Column("chirality_locked", Boolean, nullable=False, default=False),
)

regions = Table(
    "regions",
    metadata,
    Column("id", Text, primary_key=True),
    Column("universe_id", Text, ForeignKey("universes.id"), nullable=False),
    Column("x", Integer, nullable=False),
    Column("y", Integer, nullable=False),
    Column("biome_type", Text, nullable=False),
    Column("energy_level", Numeric(6, 3), nullable=False),
    Column("resource_density", Numeric(6, 3), nullable=False),
    Column("stability", Numeric(6, 3), nullable=False),
    Column("dominant_species_id", Text),
    Column("collapsed", Boolean, nullable=False, default=False),
    Column("chirality_ee", Numeric(6, 4), nullable=False, default=0),
    Column("chirality_locked", Boolean, nullable=False, default=False),
)

species = Table(
    "species",
    metadata,
    Column("id", Text, primary_key=True),
    Column("universe_id", Text, ForeignKey("universes.id"), nullable=False),
    Column("name", Text, nullable=False),
    Column("origin_region_id", Text, ForeignKey("regions.id"), nullable=False),
    Column("emerged_at_world_age", BigInteger, nullable=False),
    Column("status", Text, nullable=False),
    Column("generation", Integer, nullable=False),
    Column("parent_species_id", Text, ForeignKey("species.id")),
    Column("traits", JSON, nullable=False),
    Column("chirality", Integer, nullable=False, default=0),
    Column("heterochiral_load", Numeric(6, 4), nullable=False, default=0),
)

populations = Table(
    "populations",
    metadata,
    Column("species_id", Text, ForeignKey("species.id"), primary_key=True),
    Column("region_id", Text, ForeignKey("regions.id"), primary_key=True),
    Column("population_count", BigInteger, nullable=False),
    Column("energy_consumption", Numeric(8, 4), nullable=False),
    Column("growth_rate", Numeric(8, 4), nullable=False),
    Column("migration_pressure", Numeric(8, 4), nullable=False),
    Column("last_updated_tick", BigInteger, nullable=False),
)

events = Table(
    "events",
    metadata,
    Column("id", Text, primary_key=True),
    Column("universe_id", Text, ForeignKey("universes.id"), nullable=False),
    Column("region_id", Text, ForeignKey("regions.id")),
    Column("species_id", Text, ForeignKey("species.id")),
    Column("event_type", Text, nullable=False),
    Column("severity", Integer, nullable=False),
    Column("world_age", BigInteger, nullable=False),
    Column("tick", BigInteger, nullable=False),
    Column("title", Text, nullable=False),
    Column("summary", Text, nullable=False),
    Column("payload", JSON, nullable=False, default=dict),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)

catalyst_actions = Table(
    "catalyst_actions",
    metadata,
    Column("id", Text, primary_key=True),
    Column("universe_id", Text, ForeignKey("universes.id"), nullable=False),
    Column("region_id", Text, ForeignKey("regions.id"), nullable=False),
    Column("action_type", String, nullable=False),
    Column("user_id", Text, nullable=False),
    Column("created_at_tick", BigInteger, nullable=False),
    Column("expires_at_tick", BigInteger, nullable=False),
    Column("strength", Numeric(6, 3), nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)

catalyst_action_logs = Table(
    "catalyst_action_logs",
    metadata,
    Column("id", Text, primary_key=True),
    Column("universe_id", Text, ForeignKey("universes.id"), nullable=False),
    Column("region_id", Text, ForeignKey("regions.id"), nullable=False),
    Column("action_type", String, nullable=False),
    Column("user_id", Text, nullable=False),
    Column("day_key", Text, nullable=False),
    Column("created_at_tick", BigInteger, nullable=False),
    Column("world_age", BigInteger, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)

catalyst_user_roles = Table(
    "catalyst_user_roles",
    metadata,
    Column("universe_id", Text, ForeignKey("universes.id"), primary_key=True),
    Column("user_id", Text, primary_key=True),
    Column("role", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("granted_by", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column("updated_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)

observer_follows = Table(
    "observer_follows",
    metadata,
    Column("id", Text, primary_key=True),
    Column("universe_id", Text, ForeignKey("universes.id"), nullable=False),
    Column("user_id", Text, nullable=False),
    Column("entity_type", Text, nullable=False),
    Column("entity_id", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    UniqueConstraint(
        "universe_id",
        "user_id",
        "entity_type",
        "entity_id",
        name="uq_observer_follows_entity",
    ),
)

notification_reads = Table(
    "notification_reads",
    metadata,
    Column("universe_id", Text, ForeignKey("universes.id"), nullable=False),
    Column("user_id", Text, primary_key=True),
    Column("notification_id", Text, primary_key=True),
    Column("read_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)

universe_snapshots = Table(
    "universe_snapshots",
    metadata,
    Column("universe_id", Text, ForeignKey("universes.id"), primary_key=True),
    Column("tick", BigInteger, primary_key=True),
    Column("world_age", BigInteger, nullable=False),
    Column("region_count", Integer, nullable=False),
    Column("species_count", Integer, nullable=False),
    Column("population_count", BigInteger, nullable=False),
    Column("event_count", BigInteger, nullable=False),
    Column("payload", JSON, nullable=False, default=dict),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)

region_snapshots = Table(
    "region_snapshots",
    metadata,
    Column("universe_id", Text, ForeignKey("universes.id"), primary_key=True),
    Column("tick", BigInteger, primary_key=True),
    Column("region_id", Text, ForeignKey("regions.id"), primary_key=True),
    Column("world_age", BigInteger, nullable=False),
    Column("x", Integer, nullable=False),
    Column("y", Integer, nullable=False),
    Column("biome_type", Text, nullable=False),
    Column("energy_level", Numeric(6, 3), nullable=False),
    Column("resource_density", Numeric(6, 3), nullable=False),
    Column("stability", Numeric(6, 3), nullable=False),
    Column("dominant_species_id", Text),
    Column("collapsed", Boolean, nullable=False, default=False),
    Column("population_count", BigInteger, nullable=False),
    Column("species_count", Integer, nullable=False),
    Column("payload", JSON, nullable=False, default=dict),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)

species_snapshots = Table(
    "species_snapshots",
    metadata,
    Column("universe_id", Text, ForeignKey("universes.id"), primary_key=True),
    Column("tick", BigInteger, primary_key=True),
    Column("species_id", Text, ForeignKey("species.id"), primary_key=True),
    Column("world_age", BigInteger, nullable=False),
    Column("name", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("origin_region_id", Text, ForeignKey("regions.id"), nullable=False),
    Column("generation", Integer, nullable=False),
    Column("parent_species_id", Text),
    Column("population_count", BigInteger, nullable=False),
    Column("region_count", Integer, nullable=False),
    Column("traits", JSON, nullable=False),
    Column("payload", JSON, nullable=False, default=dict),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)

population_snapshots = Table(
    "population_snapshots",
    metadata,
    Column("universe_id", Text, ForeignKey("universes.id"), primary_key=True),
    Column("tick", BigInteger, primary_key=True),
    Column("species_id", Text, ForeignKey("species.id"), primary_key=True),
    Column("region_id", Text, ForeignKey("regions.id"), primary_key=True),
    Column("world_age", BigInteger, nullable=False),
    Column("population_count", BigInteger, nullable=False),
    Column("energy_consumption", Numeric(8, 4), nullable=False),
    Column("growth_rate", Numeric(8, 4), nullable=False),
    Column("migration_pressure", Numeric(8, 4), nullable=False),
    Column("payload", JSON, nullable=False, default=dict),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)

simulation_rule_configs = Table(
    "simulation_rule_configs",
    metadata,
    Column("id", Text, primary_key=True),
    Column("universe_id", Text, nullable=False),
    Column("revision", Integer, nullable=False),
    Column("rules_hash", Text, nullable=False),
    Column("rules", JSON, nullable=False),
    Column("applied_by", Text, nullable=False),
    Column("reason", Text),
    Column("is_active", Boolean, nullable=False, default=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)

simulation_rule_audit_logs = Table(
    "simulation_rule_audit_logs",
    metadata,
    Column("id", Text, primary_key=True),
    Column("universe_id", Text, nullable=False),
    Column("action_type", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("actor_id", Text, nullable=False),
    Column("reason", Text),
    Column("current_rules_hash", Text),
    Column("candidate_rules_hash", Text),
    Column("target_revision", Integer),
    Column("validation_errors", JSON, nullable=False, default=list),
    Column("reload_strategy", JSON, nullable=False, default=dict),
    Column("payload", JSON, nullable=False, default=dict),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)

admin_simulation_runs = Table(
    "admin_simulation_runs",
    metadata,
    Column("id", Text, primary_key=True),
    Column("universe_id", Text, ForeignKey("universes.id"), nullable=False),
    Column("action_type", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("actor_id", Text, nullable=False),
    Column("reason", Text),
    Column("requested_ticks", Integer, nullable=False, default=0),
    Column("applied_ticks", Integer, nullable=False, default=0),
    Column("seed", Integer, nullable=False),
    Column("before_tick", BigInteger, nullable=False),
    Column("after_tick", BigInteger, nullable=False),
    Column("before_world_age", BigInteger, nullable=False),
    Column("after_world_age", BigInteger, nullable=False),
    Column("payload", JSON, nullable=False, default=dict),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)

api_request_logs = Table(
    "api_request_logs",
    metadata,
    Column("id", Text, primary_key=True),
    Column("method", Text, nullable=False),
    Column("path", Text, nullable=False),
    Column("route", Text),
    Column("status_code", Integer, nullable=False),
    Column("duration_ms", Numeric(10, 3), nullable=False),
    Column("request_id", Text),
    Column("user_id", Text),
    Column("client_host", Text),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)

api_error_logs = Table(
    "api_error_logs",
    metadata,
    Column("id", Text, primary_key=True),
    Column("method", Text, nullable=False),
    Column("path", Text, nullable=False),
    Column("route", Text),
    Column("status_code", Integer, nullable=False),
    Column("error_code", Text, nullable=False),
    Column("message", Text),
    Column("request_id", Text),
    Column("payload", JSON, nullable=False, default=dict),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)

worker_run_events = Table(
    "worker_run_events",
    metadata,
    Column("id", Text, primary_key=True),
    Column("worker_id", Text, nullable=False),
    Column("universe_id", Text, ForeignKey("universes.id"), nullable=False),
    Column("event_type", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("last_tick", BigInteger, nullable=False, default=0),
    Column("last_world_age", BigInteger, nullable=False, default=0),
    Column("last_step", BigInteger, nullable=False, default=0),
    Column("error", Text),
    Column("payload", JSON, nullable=False, default=dict),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)

product_analytics_events = Table(
    "product_analytics_events",
    metadata,
    Column("id", Text, primary_key=True),
    Column("universe_id", Text, ForeignKey("universes.id"), nullable=False),
    Column("event_name", Text, nullable=False),
    Column("user_id", Text),
    Column("session_id", Text),
    Column("subject_type", Text),
    Column("subject_id", Text),
    Column("source", Text, nullable=False),
    Column("metadata", JSON, nullable=False, default=dict),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)

worker_heartbeats = Table(
    "worker_heartbeats",
    metadata,
    Column("worker_id", Text, primary_key=True),
    Column("universe_id", Text, ForeignKey("universes.id"), nullable=False),
    Column("status", Text, nullable=False),
    Column("last_tick", BigInteger, nullable=False),
    Column("last_world_age", BigInteger, nullable=False),
    Column("last_step", BigInteger, nullable=False),
    Column("last_error", Text),
    Column("updated_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)
