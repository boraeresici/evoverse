from __future__ import annotations

import os
from collections.abc import Iterable
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Engine, and_, create_engine, delete, desc, func, or_, select, update
from sqlalchemy.pool import StaticPool


# Hot-path bounds for the worker loop. See docs/PERFORMANCE_LOOP.md.
#
# MAX_LOADED_EVENTS caps how many events are hydrated into the in-memory working
# set on every `load_alpha`. Full history stays in the DB; only the most recent
# slice is rebuilt each reload so the per-tick reload cost stays constant instead
# of growing forever with the event log.
MAX_LOADED_EVENTS = int(os.getenv("EVOVERSE_MAX_LOADED_EVENTS", "2000"))

# MAX_STORED_EVENTS is an optional DB-side retention cap. 0 (the default) keeps
# every event forever; set a positive value to prune the oldest rows on write and
# bound on-disk growth. Keep it >= MAX_LOADED_EVENTS so a reload can always fill
# the in-memory slice.
MAX_STORED_EVENTS = int(os.getenv("EVOVERSE_MAX_STORED_EVENTS", "0"))

# How many historical snapshot frames to keep, across all of world history. See
# docs/PERFORMANCE_LOOP.md.
#
# A frame is one set of universe/region/species snapshots at a single tick.
# Writing one per tick grew without bound (~36M rows/day) to serve a scrubber that
# can address ~100 frames, so frames are instead kept on a stride: only ticks
# where `tick % stride == 0` are stored, and stride is the smallest power of two
# that fits history into this budget. Stride doubles as the universe ages, which
# holds the frame count between BUDGET/2 and BUDGET forever -- history keeps its
# full span and only loses resolution, which is the tradeoff the scrubber can
# actually perceive. Recent fidelity does not depend on this: the live view reads
# current state directly, not snapshots.
SNAPSHOT_FRAME_BUDGET = int(os.getenv("EVOVERSE_SNAPSHOT_FRAME_BUDGET", "2000"))

# Frames removed per compaction call. Compaction deletes whole ticks, so this is
# in frames, not rows (one frame is ~420 rows at Alpha's size). Bounded so a
# stride change -- or a first run against an uncompacted backlog -- drains over
# repeated calls instead of one transaction that would stall the database.
SNAPSHOT_COMPACT_BATCH = int(os.getenv("EVOVERSE_SNAPSHOT_COMPACT_BATCH", "200"))

from app.domain import (
    AlphaState,
    BiomeType,
    CatalystAction,
    CatalystActionType,
    Era,
    Event,
    EventType,
    Population,
    Region,
    Species,
    SpeciesStatus,
    Traits,
    Universe,
)
from app.persistence.schema import (
    admin_simulation_runs,
    api_error_logs,
    api_request_logs,
    catalyst_action_logs,
    catalyst_actions,
    catalyst_user_roles,
    diagnostics_runs,
    events,
    metadata,
    notification_reads,
    observer_follows,
    populations,
    population_snapshots,
    product_analytics_events,
    region_snapshots,
    regions,
    species,
    species_snapshots,
    simulation_rule_audit_logs,
    simulation_rule_configs,
    universe_snapshots,
    universes,
    worker_run_events,
    worker_heartbeats,
)


class AlphaStateConflictError(RuntimeError):
    def __init__(self, universe_id: str, expected_tick: int, actual_tick: int | None) -> None:
        self.universe_id = universe_id
        self.expected_tick = expected_tick
        self.actual_tick = actual_tick
        super().__init__(
            f"Alpha state conflict for {universe_id}: expected tick {expected_tick}, actual tick {actual_tick}"
        )


class AlphaStateRepository:
    def __init__(
        self,
        database_url: str,
        *,
        create_schema: bool = False,
        echo: bool = False,
    ) -> None:
        engine_kwargs = {"future": True, "echo": echo}
        if database_url == "sqlite+pysqlite:///:memory:":
            engine_kwargs["connect_args"] = {"check_same_thread": False}
            engine_kwargs["poolclass"] = StaticPool
        self.engine: Engine = create_engine(database_url, **engine_kwargs)
        if create_schema:
            metadata.create_all(self.engine)

    @property
    def persistence_name(self) -> str:
        if self.engine.dialect.name.startswith("postgres"):
            return "postgres"
        return self.engine.dialect.name

    def load_alpha(self, *, seed: int, universe_id: str = "alpha") -> AlphaState | None:
        with self.engine.begin() as connection:
            universe_row = connection.execute(
                select(universes).where(universes.c.id == universe_id)
            ).mappings().one_or_none()
            if universe_row is None:
                return None

            region_rows = connection.execute(
                select(regions)
                .where(regions.c.universe_id == universe_id)
                .order_by(regions.c.y, regions.c.x)
            ).mappings().all()
            species_rows = connection.execute(
                select(species)
                .where(species.c.universe_id == universe_id)
                .order_by(species.c.id)
            ).mappings().all()
            population_rows = connection.execute(
                select(populations)
                .select_from(populations.join(species, populations.c.species_id == species.c.id))
                .where(species.c.universe_id == universe_id)
                .order_by(populations.c.region_id, populations.c.species_id)
            ).mappings().all()
            # Hydrate only the most recent slice of the event log. Older events
            # remain in the DB (see MAX_LOADED_EVENTS); this keeps the reload that
            # runs on every worker tick / API read O(slice) instead of O(history).
            # The newest ids carry the highest suffix, so next_event_index below
            # is still correct even though the slice is bounded.
            event_rows = connection.execute(
                select(events)
                .where(events.c.universe_id == universe_id)
                .order_by(events.c.tick.desc(), events.c.id.desc())
                .limit(MAX_LOADED_EVENTS)
            ).mappings().all()
            event_rows = list(reversed(event_rows))
            action_rows = connection.execute(
                select(catalyst_actions)
                .where(catalyst_actions.c.universe_id == universe_id)
                .order_by(catalyst_actions.c.created_at_tick, catalyst_actions.c.id)
            ).mappings().all()
            action_log_rows = connection.execute(
                select(catalyst_action_logs.c.id)
                .where(catalyst_action_logs.c.universe_id == universe_id)
                .order_by(catalyst_action_logs.c.created_at_tick, catalyst_action_logs.c.id)
            ).mappings().all()

        state = AlphaState(
            universe=Universe(
                id=universe_row["id"],
                name=universe_row["name"],
                age_years=int(universe_row["age_years"]),
                current_era=Era(universe_row["current_era"]),
                tick=int(universe_row["tick"]),
                stability_index=float(universe_row["stability_index"]),
                chirality_ee=float(universe_row["chirality_ee"]),
                homochirality_index=float(universe_row["homochirality_index"]),
                local_order_index=float(universe_row["local_order_index"]),
                domain_count=int(universe_row["domain_count"]),
                chirality_locked=bool(universe_row["chirality_locked"]),
            ),
            regions={
                row["id"]: Region(
                    id=row["id"],
                    universe_id=row["universe_id"],
                    x=int(row["x"]),
                    y=int(row["y"]),
                    biome_type=BiomeType(row["biome_type"]),
                    energy_level=float(row["energy_level"]),
                    resource_density=float(row["resource_density"]),
                    stability=float(row["stability"]),
                    dominant_species_id=row["dominant_species_id"],
                    collapsed=bool(row["collapsed"]),
                    chirality_ee=float(row["chirality_ee"]),
                    chirality_locked=bool(row["chirality_locked"]),
                )
                for row in region_rows
            },
            species={
                row["id"]: Species(
                    id=row["id"],
                    universe_id=row["universe_id"],
                    name=row["name"],
                    origin_region_id=row["origin_region_id"],
                    emerged_at_world_age=int(row["emerged_at_world_age"]),
                    status=SpeciesStatus(row["status"]),
                    generation=int(row["generation"]),
                    parent_species_id=row["parent_species_id"],
                    traits=Traits(**row["traits"]),
                    chirality=int(row["chirality"]),
                    heterochiral_load=float(row["heterochiral_load"]),
                )
                for row in species_rows
            },
            populations={
                (row["species_id"], row["region_id"]): Population(
                    species_id=row["species_id"],
                    region_id=row["region_id"],
                    population_count=int(row["population_count"]),
                    energy_consumption=float(row["energy_consumption"]),
                    growth_rate=float(row["growth_rate"]),
                    migration_pressure=float(row["migration_pressure"]),
                    last_updated_tick=int(row["last_updated_tick"]),
                )
                for row in population_rows
            },
            events=[_row_to_event(row) for row in event_rows],
            catalyst_actions=[
                CatalystAction(
                    id=row["id"],
                    universe_id=row["universe_id"],
                    region_id=row["region_id"],
                    action_type=CatalystActionType(row["action_type"]),
                    created_at_tick=int(row["created_at_tick"]),
                    expires_at_tick=int(row["expires_at_tick"]),
                    strength=float(row["strength"]),
                    user_id=row["user_id"],
                )
                for row in action_rows
            ],
            seed=seed,
            next_event_index=_max_suffix(row["id"] for row in event_rows),
            next_species_index=_max_suffix(row["id"] for row in species_rows),
            next_action_index=max(
                _max_suffix(row["id"] for row in action_rows),
                _max_suffix(row["id"] for row in action_log_rows),
            ),
        )
        return state

    def events_page(
        self,
        *,
        universe_id: str = "alpha",
        limit: int,
        offset: int = 0,
        cursor: str | None = None,
        region_id: str | None = None,
        species_id: str | None = None,
        min_world_age: int | None = None,
    ) -> dict:
        """Keyset (cursor) pagination over the event log, straight from the DB.

        Ordered newest-first by ``(tick, id)`` — the strict total order backed by
        the ``idx_events_*_tick`` indexes. A ``cursor`` walks arbitrarily deep at
        constant per-page cost (``WHERE (tick, id) < (cursor)``); without one we
        fall back to ``OFFSET`` so the legacy offset contract still works to any
        depth (just slower deep). Returns domain ``Event`` objects so the caller
        serializes them exactly like in-memory events.
        """
        limit = max(1, min(limit, 100))
        conditions = [events.c.universe_id == universe_id]
        if region_id is not None:
            conditions.append(events.c.region_id == region_id)
        if species_id is not None:
            conditions.append(events.c.species_id == species_id)
        if min_world_age is not None:
            conditions.append(events.c.world_age >= min_world_age)

        decoded = decode_event_cursor(cursor)
        with self.engine.begin() as connection:
            total = connection.execute(
                select(func.count()).select_from(events).where(*conditions)
            ).scalar() or 0

            query = select(events).where(*conditions)
            effective_offset = 0
            if decoded is not None:
                cursor_tick, cursor_id = decoded
                query = query.where(
                    or_(
                        events.c.tick < cursor_tick,
                        and_(events.c.tick == cursor_tick, events.c.id < cursor_id),
                    )
                )
            else:
                effective_offset = max(0, offset)
            query = query.order_by(events.c.tick.desc(), events.c.id.desc())
            if effective_offset:
                query = query.offset(effective_offset)
            # One extra row tells us whether another page exists without a re-count.
            rows = connection.execute(query.limit(limit + 1)).mappings().all()

        has_more = len(rows) > limit
        items = [_row_to_event(row) for row in rows[:limit]]
        next_cursor = (
            encode_event_cursor(items[-1].tick, items[-1].id)
            if has_more and items
            else None
        )
        next_offset = (
            effective_offset + limit if decoded is None and has_more else None
        )
        return {
            "items": items,
            "pagination": {
                "limit": limit,
                "offset": effective_offset,
                "total": int(total),
                "hasMore": has_more,
                "nextOffset": next_offset,
                "nextCursor": next_cursor,
            },
        }

    def save_alpha(
        self,
        state: AlphaState,
        *,
        expected_tick: int | None = None,
        catalyst_action_log: dict | None = None,
    ) -> None:
        with self.engine.begin() as connection:
            universe_id = state.universe.id
            existing_universe = connection.execute(
                select(universes.c.tick).where(universes.c.id == universe_id)
            ).scalar_one_or_none()
            if (
                expected_tick is not None
                and existing_universe is not None
                and int(existing_universe) != expected_tick
            ):
                raise AlphaStateConflictError(
                    universe_id=universe_id,
                    expected_tick=expected_tick,
                    actual_tick=int(existing_universe),
                )

            connection.execute(
                delete(catalyst_actions).where(catalyst_actions.c.universe_id == universe_id)
            )
            existing_species_ids = select(species.c.id).where(species.c.universe_id == universe_id)
            connection.execute(
                delete(populations).where(populations.c.species_id.in_(existing_species_ids))
            )

            _upsert(
                connection,
                universes,
                ["id"],
                {
                    "id": state.universe.id,
                    "name": state.universe.name,
                    "age_years": state.universe.age_years,
                    "current_era": state.universe.current_era.value,
                    "tick": state.universe.tick,
                    "stability_index": state.universe.stability_index,
                    "chirality_ee": state.universe.chirality_ee,
                    "homochirality_index": state.universe.homochirality_index,
                    "local_order_index": state.universe.local_order_index,
                    "domain_count": state.universe.domain_count,
                    "chirality_locked": state.universe.chirality_locked,
                },
            )
            for region in state.regions.values():
                _upsert(
                    connection,
                    regions,
                    ["id"],
                    {
                        "id": region.id,
                        "universe_id": region.universe_id,
                        "x": region.x,
                        "y": region.y,
                        "biome_type": region.biome_type.value,
                        "energy_level": region.energy_level,
                        "resource_density": region.resource_density,
                        "stability": region.stability,
                        "dominant_species_id": region.dominant_species_id,
                        "collapsed": region.collapsed,
                        "chirality_ee": region.chirality_ee,
                        "chirality_locked": region.chirality_locked,
                    },
                )
            for item in state.species.values():
                _upsert(
                    connection,
                    species,
                    ["id"],
                    {
                        "id": item.id,
                        "universe_id": item.universe_id,
                        "name": item.name,
                        "origin_region_id": item.origin_region_id,
                        "emerged_at_world_age": item.emerged_at_world_age,
                        "status": item.status.value,
                        "generation": item.generation,
                        "parent_species_id": item.parent_species_id,
                        "traits": item.traits.to_public(),
                        "chirality": item.chirality,
                        "heterochiral_load": item.heterochiral_load,
                    },
                )
            if state.populations:
                connection.execute(
                    populations.insert(),
                    [
                        {
                            "species_id": population.species_id,
                            "region_id": population.region_id,
                            "population_count": population.population_count,
                            "energy_consumption": population.energy_consumption,
                            "growth_rate": population.growth_rate,
                            "migration_pressure": population.migration_pressure,
                            "last_updated_tick": population.last_updated_tick,
                        }
                        for population in state.populations.values()
                    ],
                )
            new_events = _unpersisted_events(connection, universe_id, state.events)
            if new_events:
                connection.execute(
                    events.insert(),
                    [
                        {
                            "id": event.id,
                            "universe_id": event.universe_id,
                            "region_id": event.region_id,
                            "species_id": event.species_id,
                            "event_type": event.event_type.value,
                            "severity": event.severity,
                            "world_age": event.world_age,
                            "tick": event.tick,
                            "title": event.title,
                            "summary": event.summary,
                            "payload": event.payload,
                        }
                        for event in new_events
                    ],
                )
                if MAX_STORED_EVENTS > 0:
                    _prune_events(connection, universe_id, keep=MAX_STORED_EVENTS)
            if state.catalyst_actions:
                connection.execute(
                    catalyst_actions.insert(),
                    [
                        {
                            "id": action.id,
                            "universe_id": action.universe_id,
                            "region_id": action.region_id,
                            "action_type": action.action_type.value,
                            "user_id": action.user_id,
                            "created_at_tick": action.created_at_tick,
                            "expires_at_tick": action.expires_at_tick,
                            "strength": action.strength,
                        }
                        for action in state.catalyst_actions
                    ],
                )
            if catalyst_action_log:
                existing_log = connection.execute(
                    select(catalyst_action_logs.c.id).where(
                        catalyst_action_logs.c.id == catalyst_action_log["id"]
                    )
                ).scalar_one_or_none()
                if existing_log is None:
                    connection.execute(catalyst_action_logs.insert(), [catalyst_action_log])
            _insert_snapshot(connection, state)

    def reset_alpha(
        self,
        state: AlphaState,
        *,
        preserve_user_state: bool = True,
    ) -> None:
        universe_id = state.universe.id
        with self.engine.begin() as connection:
            _delete_alpha_state(
                connection,
                universe_id=universe_id,
                preserve_user_state=preserve_user_state,
            )
        self.save_alpha(state)

    def snapshot_count(self, universe_id: str = "alpha") -> int:
        with self.engine.begin() as connection:
            return int(
                connection.execute(
                    select(func.count())
                    .select_from(universe_snapshots)
                    .where(universe_snapshots.c.universe_id == universe_id)
                ).scalar_one()
            )

    def latest_snapshot(self, universe_id: str = "alpha") -> dict | None:
        with self.engine.begin() as connection:
            row = connection.execute(
                select(universe_snapshots)
                .where(universe_snapshots.c.universe_id == universe_id)
                .order_by(desc(universe_snapshots.c.tick))
                .limit(1)
            ).mappings().one_or_none()
        return dict(row) if row else None

    def snapshots(
        self,
        universe_id: str = "alpha",
        *,
        limit: int = 50,
        offset: int = 0,
        from_world_age: int | None = None,
        to_world_age: int | None = None,
    ) -> dict:
        criteria = [universe_snapshots.c.universe_id == universe_id]
        if from_world_age is not None:
            criteria.append(universe_snapshots.c.world_age >= from_world_age)
        if to_world_age is not None:
            criteria.append(universe_snapshots.c.world_age <= to_world_age)

        with self.engine.begin() as connection:
            total = int(
                connection.execute(
                    select(func.count())
                    .select_from(universe_snapshots)
                    .where(*criteria)
                ).scalar_one()
            )
            rows = connection.execute(
                select(universe_snapshots)
                .where(*criteria)
                .order_by(desc(universe_snapshots.c.tick))
                .limit(limit)
                .offset(offset)
            ).mappings().all()
        return {
            "items": [dict(row) for row in rows],
            "total": total,
        }

    def save_diagnostics_run(
        self,
        *,
        universe_id: str,
        kind: str,
        seed: int,
        ticks: int,
        verdict: str,
        duration_ms: float,
        payload: dict,
    ) -> None:
        """Park the latest result for ``kind``, replacing any previous one.

        Upsert rather than insert: the table is keyed on (universe_id, kind) so it
        holds one row per diagnostic and never grows. Keeping a history would be a
        separate, deliberate feature.
        """
        with self.engine.begin() as connection:
            _upsert(
                connection,
                diagnostics_runs,
                ["universe_id", "kind"],
                {
                    "universe_id": universe_id,
                    "kind": kind,
                    "seed": seed,
                    "ticks": ticks,
                    "verdict": verdict,
                    "duration_ms": duration_ms,
                    "payload": payload,
                    "measured_at": datetime.now(UTC),
                },
            )

    def diagnostics_run(self, kind: str, universe_id: str = "alpha") -> dict | None:
        with self.engine.begin() as connection:
            row = connection.execute(
                select(diagnostics_runs).where(
                    diagnostics_runs.c.universe_id == universe_id,
                    diagnostics_runs.c.kind == kind,
                )
            ).mappings().one_or_none()
        return dict(row) if row is not None else None

    def compact_snapshots(self, universe_id: str = "alpha", *, budget: int | None = None) -> dict:
        """Drop up to SNAPSHOT_COMPACT_BATCH frames the current stride no longer keeps.

        Idempotent: it recomputes the stride from the newest tick and removes
        whatever no longer sits on the grid, so the same call both maintains a
        live universe (a handful of frames each time the stride doubles) and
        drains a backlog written before striding existed (many calls, batch by
        batch). Returns the stride in force and how many frames went.
        """
        frame_budget = budget if budget is not None else SNAPSHOT_FRAME_BUDGET
        with self.engine.begin() as connection:
            stride = snapshot_stride(
                _snapshot_frame_tick(connection, universe_id),
                budget=frame_budget,
            )
            if stride == 1:
                return {"stride": 1, "framesDropped": 0}
            doomed = connection.execute(
                select(universe_snapshots.c.tick)
                .where(
                    universe_snapshots.c.universe_id == universe_id,
                    universe_snapshots.c.tick % stride != 0,
                )
                .order_by(universe_snapshots.c.tick)
                .limit(SNAPSHOT_COMPACT_BATCH)
            ).scalars().all()
            if not doomed:
                return {"stride": stride, "framesDropped": 0}
            # Detail rows are reached by their (universe_id, tick, ...) primary
            # key, so only the frame scan above touches a non-indexed predicate --
            # and it runs against universe_snapshots, which the budget keeps small.
            for table in (
                population_snapshots,
                region_snapshots,
                species_snapshots,
                universe_snapshots,
            ):
                connection.execute(
                    delete(table).where(
                        table.c.universe_id == universe_id,
                        table.c.tick.in_(doomed),
                    )
                )
        return {"stride": stride, "framesDropped": len(doomed)}

    def snapshot_details(self, tick: int, universe_id: str = "alpha") -> dict | None:
        with self.engine.begin() as connection:
            summary = connection.execute(
                select(universe_snapshots).where(
                    universe_snapshots.c.universe_id == universe_id,
                    universe_snapshots.c.tick == tick,
                )
            ).mappings().one_or_none()
            if summary is None:
                return None
            region_rows = connection.execute(
                select(region_snapshots)
                .where(
                    region_snapshots.c.universe_id == universe_id,
                    region_snapshots.c.tick == tick,
                )
                .order_by(region_snapshots.c.y, region_snapshots.c.x)
            ).mappings().all()
            species_rows = connection.execute(
                select(species_snapshots)
                .where(
                    species_snapshots.c.universe_id == universe_id,
                    species_snapshots.c.tick == tick,
                )
                .order_by(desc(species_snapshots.c.population_count), species_snapshots.c.species_id)
            ).mappings().all()
            population_rows = connection.execute(
                select(population_snapshots)
                .where(
                    population_snapshots.c.universe_id == universe_id,
                    population_snapshots.c.tick == tick,
                )
                .order_by(
                    desc(population_snapshots.c.population_count),
                    population_snapshots.c.species_id,
                    population_snapshots.c.region_id,
                )
            ).mappings().all()
        return {
            "snapshot": dict(summary),
            "regions": [dict(row) for row in region_rows],
            "species": [dict(row) for row in species_rows],
            "populations": [dict(row) for row in population_rows],
        }

    def snapshot_detail_counts(self, tick: int, universe_id: str = "alpha") -> dict:
        with self.engine.begin() as connection:
            return {
                "region_snapshots": int(
                    connection.execute(
                        select(func.count())
                        .select_from(region_snapshots)
                        .where(
                            region_snapshots.c.universe_id == universe_id,
                            region_snapshots.c.tick == tick,
                        )
                    ).scalar_one()
                ),
                "species_snapshots": int(
                    connection.execute(
                        select(func.count())
                        .select_from(species_snapshots)
                        .where(
                            species_snapshots.c.universe_id == universe_id,
                            species_snapshots.c.tick == tick,
                        )
                    ).scalar_one()
                ),
                "population_snapshots": int(
                    connection.execute(
                        select(func.count())
                        .select_from(population_snapshots)
                        .where(
                            population_snapshots.c.universe_id == universe_id,
                            population_snapshots.c.tick == tick,
                        )
                    ).scalar_one()
                ),
            }

    def record_worker_heartbeat(
        self,
        *,
        worker_id: str,
        universe_id: str,
        status: str,
        last_tick: int,
        last_world_age: int,
        last_step: int,
        last_error: str | None = None,
    ) -> None:
        updated_at = datetime.now(UTC)
        with self.engine.begin() as connection:
            _upsert(
                connection,
                worker_heartbeats,
                ["worker_id"],
                {
                    "worker_id": worker_id,
                    "universe_id": universe_id,
                    "status": status,
                    "last_tick": last_tick,
                    "last_world_age": last_world_age,
                    "last_step": last_step,
                    "last_error": last_error,
                    "updated_at": updated_at,
                },
            )

    def latest_worker_heartbeat(self, universe_id: str = "alpha") -> dict | None:
        with self.engine.begin() as connection:
            row = connection.execute(
                select(worker_heartbeats)
                .where(worker_heartbeats.c.universe_id == universe_id)
                .order_by(desc(worker_heartbeats.c.updated_at))
                .limit(1)
            ).mappings().one_or_none()
        return dict(row) if row else None

    def record_admin_simulation_run(
        self,
        *,
        universe_id: str,
        action_type: str,
        status: str,
        actor_id: str,
        reason: str | None,
        requested_ticks: int,
        applied_ticks: int,
        seed: int,
        before_tick: int,
        after_tick: int,
        before_world_age: int,
        after_world_age: int,
        payload: dict | None = None,
    ) -> dict:
        row = {
            "id": f"admin-run-{uuid4().hex}",
            "universe_id": universe_id,
            "action_type": action_type,
            "status": status,
            "actor_id": actor_id,
            "reason": reason,
            "requested_ticks": requested_ticks,
            "applied_ticks": applied_ticks,
            "seed": seed,
            "before_tick": before_tick,
            "after_tick": after_tick,
            "before_world_age": before_world_age,
            "after_world_age": after_world_age,
            "payload": payload or {},
            "created_at": datetime.now(UTC),
        }
        with self.engine.begin() as connection:
            connection.execute(admin_simulation_runs.insert(), [row])
        return row

    def admin_simulation_runs(
        self,
        universe_id: str = "alpha",
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        with self.engine.begin() as connection:
            total = int(
                connection.execute(
                    select(func.count())
                    .select_from(admin_simulation_runs)
                    .where(admin_simulation_runs.c.universe_id == universe_id)
                ).scalar_one()
            )
            rows = connection.execute(
                select(admin_simulation_runs)
                .where(admin_simulation_runs.c.universe_id == universe_id)
                .order_by(desc(admin_simulation_runs.c.created_at))
                .limit(limit)
                .offset(offset)
            ).mappings().all()
        return {
            "items": [dict(row) for row in rows],
            "total": total,
        }

    def record_api_request_log(
        self,
        *,
        method: str,
        path: str,
        route: str | None,
        status_code: int,
        duration_ms: float,
        request_id: str | None = None,
        user_id: str | None = None,
        client_host: str | None = None,
    ) -> dict:
        row = {
            "id": f"req-{uuid4().hex}",
            "method": method,
            "path": path,
            "route": route,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "request_id": request_id,
            "user_id": user_id,
            "client_host": client_host,
            "created_at": datetime.now(UTC),
        }
        with self.engine.begin() as connection:
            connection.execute(api_request_logs.insert(), [row])
        return row

    def api_request_logs_page(self, *, limit: int = 50, offset: int = 0) -> dict:
        with self.engine.begin() as connection:
            total = int(connection.execute(select(func.count()).select_from(api_request_logs)).scalar_one())
            rows = connection.execute(
                select(api_request_logs)
                .order_by(desc(api_request_logs.c.created_at))
                .limit(limit)
                .offset(offset)
            ).mappings().all()
        return {
            "items": [dict(row) for row in rows],
            "total": total,
        }

    def api_request_summary(self) -> dict:
        with self.engine.begin() as connection:
            total = int(connection.execute(select(func.count()).select_from(api_request_logs)).scalar_one())
            errors_4xx = int(
                connection.execute(
                    select(func.count())
                    .select_from(api_request_logs)
                    .where(api_request_logs.c.status_code >= 400, api_request_logs.c.status_code < 500)
                ).scalar_one()
            )
            errors_5xx = int(
                connection.execute(
                    select(func.count())
                    .select_from(api_request_logs)
                    .where(api_request_logs.c.status_code >= 500)
                ).scalar_one()
            )
            avg_duration = connection.execute(
                select(func.avg(api_request_logs.c.duration_ms))
            ).scalar_one()
            status_rows = connection.execute(
                select(api_request_logs.c.status_code, func.count())
                .group_by(api_request_logs.c.status_code)
                .order_by(api_request_logs.c.status_code)
            ).all()
        return {
            "total": total,
            "errors4xx": errors_4xx,
            "errors5xx": errors_5xx,
            "averageDurationMs": float(avg_duration or 0.0),
            "statusCodes": {str(status): int(count) for status, count in status_rows},
        }

    def record_api_error_log(
        self,
        *,
        method: str,
        path: str,
        route: str | None,
        status_code: int,
        error_code: str,
        message: str | None = None,
        request_id: str | None = None,
        payload: dict | None = None,
    ) -> dict:
        row = {
            "id": f"err-{uuid4().hex}",
            "method": method,
            "path": path,
            "route": route,
            "status_code": status_code,
            "error_code": error_code,
            "message": message,
            "request_id": request_id,
            "payload": payload or {},
            "created_at": datetime.now(UTC),
        }
        with self.engine.begin() as connection:
            connection.execute(api_error_logs.insert(), [row])
        return row

    def api_error_logs_page(self, *, limit: int = 50, offset: int = 0) -> dict:
        with self.engine.begin() as connection:
            total = int(connection.execute(select(func.count()).select_from(api_error_logs)).scalar_one())
            rows = connection.execute(
                select(api_error_logs)
                .order_by(desc(api_error_logs.c.created_at))
                .limit(limit)
                .offset(offset)
            ).mappings().all()
        return {
            "items": [dict(row) for row in rows],
            "total": total,
        }

    def api_error_summary(self) -> dict:
        with self.engine.begin() as connection:
            total = int(connection.execute(select(func.count()).select_from(api_error_logs)).scalar_one())
            code_rows = connection.execute(
                select(api_error_logs.c.error_code, func.count())
                .group_by(api_error_logs.c.error_code)
                .order_by(api_error_logs.c.error_code)
            ).all()
        return {
            "total": total,
            "errorCodes": {str(code): int(count) for code, count in code_rows},
        }

    def record_worker_run_event(
        self,
        *,
        worker_id: str,
        universe_id: str,
        event_type: str,
        status: str,
        last_tick: int = 0,
        last_world_age: int = 0,
        last_step: int = 0,
        error: str | None = None,
        payload: dict | None = None,
    ) -> dict:
        row = {
            "id": f"worker-event-{uuid4().hex}",
            "worker_id": worker_id,
            "universe_id": universe_id,
            "event_type": event_type,
            "status": status,
            "last_tick": last_tick,
            "last_world_age": last_world_age,
            "last_step": last_step,
            "error": error,
            "payload": payload or {},
            "created_at": datetime.now(UTC),
        }
        with self.engine.begin() as connection:
            connection.execute(worker_run_events.insert(), [row])
        return row

    def worker_run_events_page(
        self,
        universe_id: str = "alpha",
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        with self.engine.begin() as connection:
            total = int(
                connection.execute(
                    select(func.count())
                    .select_from(worker_run_events)
                    .where(worker_run_events.c.universe_id == universe_id)
                ).scalar_one()
            )
            rows = connection.execute(
                select(worker_run_events)
                .where(worker_run_events.c.universe_id == universe_id)
                .order_by(desc(worker_run_events.c.created_at))
                .limit(limit)
                .offset(offset)
            ).mappings().all()
        return {
            "items": [dict(row) for row in rows],
            "total": total,
        }

    def worker_run_summary(self, universe_id: str = "alpha") -> dict:
        with self.engine.begin() as connection:
            rows = connection.execute(
                select(worker_run_events.c.event_type, func.count())
                .where(worker_run_events.c.universe_id == universe_id)
                .group_by(worker_run_events.c.event_type)
            ).all()
        counts = {str(event_type): int(count) for event_type, count in rows}
        return {
            "starts": counts.get("start", 0),
            "completions": counts.get("complete", 0),
            "crashes": counts.get("error", 0),
            "restarts": max(0, counts.get("start", 0) - 1),
            "events": counts,
        }

    def record_product_analytics_event(
        self,
        *,
        universe_id: str,
        event_name: str,
        user_id: str | None = None,
        session_id: str | None = None,
        subject_type: str | None = None,
        subject_id: str | None = None,
        source: str = "api",
        metadata: dict | None = None,
    ) -> dict:
        row = {
            "id": f"analytics-{uuid4().hex}",
            "universe_id": universe_id,
            "event_name": event_name,
            "user_id": user_id,
            "session_id": session_id,
            "subject_type": subject_type,
            "subject_id": subject_id,
            "source": source,
            "metadata": metadata or {},
            "created_at": datetime.now(UTC),
        }
        with self.engine.begin() as connection:
            connection.execute(product_analytics_events.insert(), [row])
        return row

    def product_analytics_events_page(
        self,
        universe_id: str = "alpha",
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        with self.engine.begin() as connection:
            total = int(
                connection.execute(
                    select(func.count())
                    .select_from(product_analytics_events)
                    .where(product_analytics_events.c.universe_id == universe_id)
                ).scalar_one()
            )
            rows = connection.execute(
                select(product_analytics_events)
                .where(product_analytics_events.c.universe_id == universe_id)
                .order_by(desc(product_analytics_events.c.created_at))
                .limit(limit)
                .offset(offset)
            ).mappings().all()
        return {
            "items": [dict(row) for row in rows],
            "total": total,
        }

    def product_analytics_summary(self, universe_id: str = "alpha") -> dict:
        with self.engine.begin() as connection:
            rows = connection.execute(
                select(product_analytics_events.c.event_name, func.count())
                .where(product_analytics_events.c.universe_id == universe_id)
                .group_by(product_analytics_events.c.event_name)
            ).all()
        counts = {str(name): int(count) for name, count in rows}
        landing = counts.get("landing_view", 0)
        details = counts.get("detail_view", 0)
        follows = counts.get("follow", 0)
        return {
            "events": counts,
            "landingToDetailRate": _ratio(details, landing),
            "followRate": _ratio(follows, details),
            "catalystUsage": counts.get("catalyst_action", 0),
            "replayInteractions": counts.get("replay_interaction", 0),
        }

    def catalyst_action_count(
        self,
        *,
        user_id: str,
        action_type: str,
        day_key: str,
    ) -> int:
        with self.engine.begin() as connection:
            return int(
                connection.execute(
                    select(func.count())
                    .select_from(catalyst_action_logs)
                    .where(
                        catalyst_action_logs.c.user_id == user_id,
                        catalyst_action_logs.c.action_type == action_type,
                        catalyst_action_logs.c.day_key == day_key,
                    )
                ).scalar_one()
            )

    def catalyst_action_logs_for_user(
        self,
        *,
        user_id: str,
        universe_id: str = "alpha",
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        with self.engine.begin() as connection:
            total = int(
                connection.execute(
                    select(func.count())
                    .select_from(catalyst_action_logs)
                    .where(
                        catalyst_action_logs.c.universe_id == universe_id,
                        catalyst_action_logs.c.user_id == user_id,
                    )
                ).scalar_one()
            )
            rows = connection.execute(
                select(catalyst_action_logs)
                .where(
                    catalyst_action_logs.c.universe_id == universe_id,
                    catalyst_action_logs.c.user_id == user_id,
                )
                .order_by(desc(catalyst_action_logs.c.created_at_tick), desc(catalyst_action_logs.c.id))
                .limit(limit)
                .offset(offset)
            ).mappings().all()
        return {
            "items": [dict(row) for row in rows],
            "total": total,
        }

    def catalyst_action_log(
        self,
        *,
        action_id: str,
        user_id: str | None = None,
        universe_id: str = "alpha",
    ) -> dict | None:
        criteria = [
            catalyst_action_logs.c.universe_id == universe_id,
            catalyst_action_logs.c.id == action_id,
        ]
        if user_id is not None:
            criteria.append(catalyst_action_logs.c.user_id == user_id)
        with self.engine.begin() as connection:
            row = connection.execute(
                select(catalyst_action_logs)
                .where(*criteria)
                .limit(1)
            ).mappings().one_or_none()
        return dict(row) if row else None

    def catalyst_user_role(
        self,
        *,
        user_id: str,
        universe_id: str = "alpha",
    ) -> dict | None:
        with self.engine.begin() as connection:
            row = connection.execute(
                select(catalyst_user_roles)
                .where(
                    catalyst_user_roles.c.universe_id == universe_id,
                    catalyst_user_roles.c.user_id == user_id,
                )
                .limit(1)
            ).mappings().one_or_none()
        return dict(row) if row else None

    def save_catalyst_user_role(
        self,
        *,
        user_id: str,
        role: str,
        status: str,
        granted_by: str,
        universe_id: str = "alpha",
    ) -> dict:
        now = datetime.now(UTC)
        row = {
            "universe_id": universe_id,
            "user_id": user_id,
            "role": role,
            "status": status,
            "granted_by": granted_by,
            "updated_at": now,
        }
        with self.engine.begin() as connection:
            existing = connection.execute(
                select(catalyst_user_roles.c.created_at)
                .where(
                    catalyst_user_roles.c.universe_id == universe_id,
                    catalyst_user_roles.c.user_id == user_id,
                )
                .limit(1)
            ).scalar_one_or_none()
            if existing is None:
                row["created_at"] = now
            _upsert(
                connection,
                catalyst_user_roles,
                ["universe_id", "user_id"],
                row,
            )
            saved = connection.execute(
                select(catalyst_user_roles)
                .where(
                    catalyst_user_roles.c.universe_id == universe_id,
                    catalyst_user_roles.c.user_id == user_id,
                )
                .limit(1)
            ).mappings().one()
        return dict(saved)

    def observer_follows(
        self,
        *,
        user_id: str,
        universe_id: str = "alpha",
    ) -> list[dict]:
        with self.engine.begin() as connection:
            rows = connection.execute(
                select(observer_follows)
                .where(
                    observer_follows.c.universe_id == universe_id,
                    observer_follows.c.user_id == user_id,
                )
                .order_by(observer_follows.c.entity_type, desc(observer_follows.c.created_at))
            ).mappings().all()
        return [dict(row) for row in rows]

    def save_observer_follow(
        self,
        *,
        user_id: str,
        entity_type: str,
        entity_id: str,
        universe_id: str = "alpha",
    ) -> dict:
        with self.engine.begin() as connection:
            existing = connection.execute(
                select(observer_follows)
                .where(
                    observer_follows.c.universe_id == universe_id,
                    observer_follows.c.user_id == user_id,
                    observer_follows.c.entity_type == entity_type,
                    observer_follows.c.entity_id == entity_id,
                )
                .limit(1)
            ).mappings().one_or_none()
            if existing is not None:
                return dict(existing)
            row = {
                "id": f"follow-{uuid4().hex}",
                "universe_id": universe_id,
                "user_id": user_id,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "created_at": datetime.now(UTC),
            }
            connection.execute(observer_follows.insert(), [row])
        return row

    def delete_observer_follow(
        self,
        *,
        user_id: str,
        entity_type: str,
        entity_id: str,
        universe_id: str = "alpha",
    ) -> bool:
        with self.engine.begin() as connection:
            result = connection.execute(
                delete(observer_follows).where(
                    observer_follows.c.universe_id == universe_id,
                    observer_follows.c.user_id == user_id,
                    observer_follows.c.entity_type == entity_type,
                    observer_follows.c.entity_id == entity_id,
                )
            )
        return result.rowcount > 0

    def notification_reads(
        self,
        *,
        user_id: str,
        universe_id: str = "alpha",
    ) -> dict[str, dict]:
        with self.engine.begin() as connection:
            rows = connection.execute(
                select(notification_reads)
                .where(
                    notification_reads.c.universe_id == universe_id,
                    notification_reads.c.user_id == user_id,
                )
            ).mappings().all()
        return {row["notification_id"]: dict(row) for row in rows}

    def record_notification_read(
        self,
        *,
        user_id: str,
        notification_id: str,
        universe_id: str = "alpha",
    ) -> dict:
        read_at = datetime.now(UTC)
        row = {
            "universe_id": universe_id,
            "user_id": user_id,
            "notification_id": notification_id,
            "read_at": read_at,
        }
        with self.engine.begin() as connection:
            _upsert(
                connection,
                notification_reads,
                ["user_id", "notification_id"],
                row,
            )
        return row

    def latest_simulation_rules_config(self, universe_id: str = "alpha") -> dict | None:
        with self.engine.begin() as connection:
            row = connection.execute(
                select(simulation_rule_configs)
                .where(
                    simulation_rule_configs.c.universe_id == universe_id,
                    simulation_rule_configs.c.is_active == True,  # noqa: E712
                )
                .order_by(desc(simulation_rule_configs.c.revision))
                .limit(1)
            ).mappings().one_or_none()
        return dict(row) if row else None

    def simulation_rules_config_by_revision(
        self,
        revision: int,
        universe_id: str = "alpha",
    ) -> dict | None:
        with self.engine.begin() as connection:
            row = connection.execute(
                select(simulation_rule_configs)
                .where(
                    simulation_rule_configs.c.universe_id == universe_id,
                    simulation_rule_configs.c.revision == revision,
                )
                .limit(1)
            ).mappings().one_or_none()
        return dict(row) if row else None

    def previous_simulation_rules_config(self, universe_id: str = "alpha") -> dict | None:
        active = self.latest_simulation_rules_config(universe_id=universe_id)
        if active is None:
            return None
        with self.engine.begin() as connection:
            row = connection.execute(
                select(simulation_rule_configs)
                .where(
                    simulation_rule_configs.c.universe_id == universe_id,
                    simulation_rule_configs.c.revision < int(active["revision"]),
                )
                .order_by(desc(simulation_rule_configs.c.revision))
                .limit(1)
            ).mappings().one_or_none()
        return dict(row) if row else None

    def simulation_rules_revisions(
        self,
        universe_id: str = "alpha",
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> dict:
        with self.engine.begin() as connection:
            total = int(
                connection.execute(
                    select(func.count())
                    .select_from(simulation_rule_configs)
                    .where(simulation_rule_configs.c.universe_id == universe_id)
                ).scalar_one()
            )
            rows = connection.execute(
                select(simulation_rule_configs)
                .where(simulation_rule_configs.c.universe_id == universe_id)
                .order_by(desc(simulation_rule_configs.c.revision))
                .limit(limit)
                .offset(offset)
            ).mappings().all()
        return {
            "items": [dict(row) for row in rows],
            "total": total,
        }

    def save_simulation_rules_config(
        self,
        *,
        universe_id: str,
        rules: dict,
        rules_hash: str,
        actor_id: str,
        reason: str | None,
    ) -> dict:
        with self.engine.begin() as connection:
            latest_revision = connection.execute(
                select(func.max(simulation_rule_configs.c.revision))
                .where(simulation_rule_configs.c.universe_id == universe_id)
            ).scalar_one()
            revision = int(latest_revision or 0) + 1
            connection.execute(
                update(simulation_rule_configs)
                .where(
                    simulation_rule_configs.c.universe_id == universe_id,
                    simulation_rule_configs.c.is_active == True,  # noqa: E712
                )
                .values(is_active=False)
            )
            row = {
                "id": f"rules-{uuid4().hex}",
                "universe_id": universe_id,
                "revision": revision,
                "rules_hash": rules_hash,
                "rules": rules,
                "applied_by": actor_id,
                "reason": reason,
                "is_active": True,
            }
            connection.execute(simulation_rule_configs.insert(), [row])
        return row

    def record_simulation_rules_audit(
        self,
        *,
        universe_id: str,
        action_type: str,
        status: str,
        actor_id: str,
        reason: str | None = None,
        current_rules_hash: str | None = None,
        candidate_rules_hash: str | None = None,
        target_revision: int | None = None,
        validation_errors: list[dict] | None = None,
        reload_strategy: dict | None = None,
        payload: dict | None = None,
    ) -> dict:
        row = {
            "id": f"rules-audit-{uuid4().hex}",
            "universe_id": universe_id,
            "action_type": action_type,
            "status": status,
            "actor_id": actor_id,
            "reason": reason,
            "current_rules_hash": current_rules_hash,
            "candidate_rules_hash": candidate_rules_hash,
            "target_revision": target_revision,
            "validation_errors": validation_errors or [],
            "reload_strategy": reload_strategy or {},
            "payload": payload or {},
        }
        with self.engine.begin() as connection:
            connection.execute(simulation_rule_audit_logs.insert(), [row])
        return row

    def simulation_rules_audit(
        self,
        universe_id: str = "alpha",
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        with self.engine.begin() as connection:
            total = int(
                connection.execute(
                    select(func.count())
                    .select_from(simulation_rule_audit_logs)
                    .where(simulation_rule_audit_logs.c.universe_id == universe_id)
                ).scalar_one()
            )
            rows = connection.execute(
                select(simulation_rule_audit_logs)
                .where(simulation_rule_audit_logs.c.universe_id == universe_id)
                .order_by(desc(simulation_rule_audit_logs.c.created_at))
                .limit(limit)
                .offset(offset)
            ).mappings().all()
        return {
            "items": [dict(row) for row in rows],
            "total": total,
        }


def create_alpha_repository(database_url: str) -> AlphaStateRepository:
    return AlphaStateRepository(database_url, create_schema=True)


def _row_to_event(row) -> Event:
    """Build a domain ``Event`` from an events-table row mapping.

    Shared by ``load_alpha`` and ``events_page`` so both apply the same payload
    normalization (via ``Event.__post_init__``) and column coercion.
    """
    return Event(
        id=row["id"],
        universe_id=row["universe_id"],
        region_id=row["region_id"],
        species_id=row["species_id"],
        event_type=EventType(row["event_type"]),
        severity=int(row["severity"]),
        world_age=int(row["world_age"]),
        tick=int(row["tick"]),
        title=row["title"],
        summary=row["summary"],
        payload=row["payload"] or {},
        created_at=str(row["created_at"]),
    )


def encode_event_cursor(tick: int, event_id: str) -> str:
    """Opaque keyset cursor for the ``(tick, id)`` total order."""
    return f"{tick}:{event_id}"


def decode_event_cursor(cursor: str | None) -> tuple[int, str] | None:
    """Parse a cursor back to ``(tick, id)``; ``None`` for missing/malformed input."""
    if not cursor:
        return None
    raw = cursor.strip()
    tick_part, _, event_id = raw.partition(":")
    if not event_id:
        return None
    try:
        return int(tick_part), event_id
    except ValueError:
        return None


def _unpersisted_events(connection, universe_id: str, state_events: list) -> list:
    """Return the events not yet stored, without shipping the whole id log to the DB.

    The event store is append-only, so any event that is not yet persisted must
    sit at or after the newest tick already stored. We therefore look up existing
    ids only at that boundary tick, which bounds the dedup query to one tick's
    worth of events instead of the entire history. The previous implementation
    built an ``IN (...)`` clause over every event id on every save, which grew
    linearly and eventually blew past the driver's bind-parameter limit.
    """
    if not state_events:
        return []
    db_max_tick = connection.execute(
        select(func.max(events.c.tick)).where(events.c.universe_id == universe_id)
    ).scalar()
    if db_max_tick is None:
        return list(state_events)
    boundary_ids = set(
        connection.execute(
            select(events.c.id).where(
                events.c.universe_id == universe_id,
                events.c.tick >= db_max_tick,
            )
        ).scalars()
    )
    return [
        event
        for event in state_events
        if event.tick > db_max_tick
        or (event.tick == db_max_tick and event.id not in boundary_ids)
    ]


def _prune_events(connection, universe_id: str, *, keep: int) -> None:
    """Delete all but the newest ``keep`` events for a universe (opt-in retention).

    Only the oldest rows are removed, so the boundary the append-only writer and
    the tail loader rely on (the newest tick) is never touched.
    """
    total = connection.execute(
        select(func.count())
        .select_from(events)
        .where(events.c.universe_id == universe_id)
    ).scalar()
    if total <= keep:
        return
    cutoff_tick, cutoff_id = connection.execute(
        select(events.c.tick, events.c.id)
        .where(events.c.universe_id == universe_id)
        .order_by(events.c.tick.desc(), events.c.id.desc())
        .offset(keep - 1)
        .limit(1)
    ).one()
    connection.execute(
        delete(events).where(
            events.c.universe_id == universe_id,
            or_(
                events.c.tick < cutoff_tick,
                and_(events.c.tick == cutoff_tick, events.c.id < cutoff_id),
            ),
        )
    )


def snapshot_stride(max_tick: int, *, budget: int | None = None) -> int:
    """Smallest power of two that fits ``max_tick`` worth of frames into ``budget``.

    Derived, never stored: any process can recompute the current stride from the
    newest tick alone, so the write path and the compaction job cannot disagree
    about which ticks are frames. Doubling (rather than growing by an arbitrary
    step) is what makes compaction non-destructive to the surviving grid -- every
    tick kept at stride 2N is also a multiple of stride N, so widening the stride
    only ever drops frames, never shifts the ones that remain.
    """
    # Resolved here rather than as a default argument so the module global stays
    # the single source of truth: a default would bind once at import and silently
    # ignore any later change to the budget.
    frame_budget = SNAPSHOT_FRAME_BUDGET if budget is None else budget
    if frame_budget <= 0:
        raise ValueError("snapshot frame budget must be positive")
    stride = 1
    while max_tick // stride > frame_budget:
        stride *= 2
    return stride


def _snapshot_frame_tick(connection, universe_id: str) -> int:
    newest = connection.execute(
        select(func.max(universe_snapshots.c.tick)).where(
            universe_snapshots.c.universe_id == universe_id
        )
    ).scalar()
    return int(newest or 0)


def _upsert(connection, table, key_columns: list[str], values: dict) -> None:
    assignments = {
        key: value for key, value in values.items() if key not in set(key_columns)
    }
    criteria = [
        getattr(table.c, key) == values[key]
        for key in key_columns
    ]
    result = connection.execute(update(table).where(*criteria).values(**assignments))
    if result.rowcount == 0:
        connection.execute(table.insert(), [values])


def _delete_alpha_state(
    connection,
    *,
    universe_id: str,
    preserve_user_state: bool,
) -> None:
    connection.execute(
        delete(population_snapshots).where(population_snapshots.c.universe_id == universe_id)
    )
    connection.execute(
        delete(species_snapshots).where(species_snapshots.c.universe_id == universe_id)
    )
    connection.execute(
        delete(region_snapshots).where(region_snapshots.c.universe_id == universe_id)
    )
    connection.execute(
        delete(universe_snapshots).where(universe_snapshots.c.universe_id == universe_id)
    )
    connection.execute(
        delete(catalyst_actions).where(catalyst_actions.c.universe_id == universe_id)
    )
    connection.execute(
        delete(catalyst_action_logs).where(catalyst_action_logs.c.universe_id == universe_id)
    )
    connection.execute(
        delete(events).where(events.c.universe_id == universe_id)
    )
    existing_species_ids = select(species.c.id).where(species.c.universe_id == universe_id)
    connection.execute(
        delete(populations).where(populations.c.species_id.in_(existing_species_ids))
    )
    connection.execute(delete(species).where(species.c.universe_id == universe_id))
    connection.execute(delete(regions).where(regions.c.universe_id == universe_id))
    if not preserve_user_state:
        connection.execute(
            delete(notification_reads).where(notification_reads.c.universe_id == universe_id)
        )
        connection.execute(
            delete(observer_follows).where(observer_follows.c.universe_id == universe_id)
        )


def _insert_snapshot(connection, state: AlphaState) -> None:
    # Frames are written on a stride, not every tick. The stride follows the
    # newest tick already on disk rather than the tick being written, so a save
    # cannot widen the stride and skip its own frame in the same call.
    stride = snapshot_stride(_snapshot_frame_tick(connection, state.universe.id))
    if state.universe.tick % stride != 0:
        return
    population_count = sum(
        population.population_count for population in state.populations.values()
    )
    region_population_totals, region_species_counts = _region_snapshot_totals(state)
    species_population_totals, species_region_counts = _species_snapshot_totals(state)
    event_count = int(
        connection.execute(
            select(func.count())
            .select_from(events)
            .where(events.c.universe_id == state.universe.id)
        ).scalar_one()
    )
    snapshot = {
        "universe_id": state.universe.id,
        "tick": state.universe.tick,
        "world_age": state.universe.age_years,
        "region_count": len(state.regions),
        "species_count": len(state.species),
        "population_count": population_count,
        "event_count": event_count,
        "payload": {
            "snapshot_model": "entity_snapshots_v1",
            "stability_index": state.universe.stability_index,
            "chirality_ee": state.universe.chirality_ee,
            "homochirality_index": state.universe.homochirality_index,
            "local_order_index": state.universe.local_order_index,
            "domain_count": state.universe.domain_count,
            "chirality_locked": state.universe.chirality_locked,
            "active_catalyst_actions": len(state.catalyst_actions),
            "region_snapshot_count": len(state.regions),
            "species_snapshot_count": len(state.species),
            "population_snapshot_count": len(state.populations),
        },
    }
    existing = connection.execute(
        select(universe_snapshots.c.tick).where(
            universe_snapshots.c.universe_id == state.universe.id,
            universe_snapshots.c.tick == state.universe.tick,
        )
    ).scalar_one_or_none()
    if existing is None:
        connection.execute(universe_snapshots.insert(), [snapshot])
    else:
        connection.execute(
            update(universe_snapshots)
            .where(
                universe_snapshots.c.universe_id == state.universe.id,
                universe_snapshots.c.tick == state.universe.tick,
            )
            .values(
                region_count=snapshot["region_count"],
                species_count=snapshot["species_count"],
                population_count=snapshot["population_count"],
                event_count=snapshot["event_count"],
                payload=snapshot["payload"],
            )
        )
    detail_existing = connection.execute(
        select(region_snapshots.c.region_id)
        .where(
            region_snapshots.c.universe_id == state.universe.id,
            region_snapshots.c.tick == state.universe.tick,
        )
        .limit(1)
    ).scalar_one_or_none()
    if detail_existing is not None:
        return

    connection.execute(
        region_snapshots.insert(),
        [
            {
                "universe_id": state.universe.id,
                "tick": state.universe.tick,
                "region_id": region.id,
                "world_age": state.universe.age_years,
                "x": region.x,
                "y": region.y,
                "biome_type": region.biome_type.value,
                "energy_level": region.energy_level,
                "resource_density": region.resource_density,
                "stability": region.stability,
                "dominant_species_id": region.dominant_species_id,
                "collapsed": region.collapsed,
                "population_count": region_population_totals.get(region.id, 0),
                "species_count": region_species_counts.get(region.id, 0),
                "payload": {
                    "life_index": round(
                        min(1.0, region_population_totals.get(region.id, 0) / 26000),
                        3,
                    ),
                    "chirality_ee": region.chirality_ee,
                    "chirality_locked": region.chirality_locked,
                },
            }
            for region in state.regions.values()
        ],
    )
    if state.species:
        connection.execute(
            species_snapshots.insert(),
            [
                {
                    "universe_id": state.universe.id,
                    "tick": state.universe.tick,
                    "species_id": item.id,
                    "world_age": state.universe.age_years,
                    "name": item.name,
                    "status": item.status.value,
                    "origin_region_id": item.origin_region_id,
                    "generation": item.generation,
                    "parent_species_id": item.parent_species_id,
                    "population_count": species_population_totals.get(item.id, 0),
                    "region_count": species_region_counts.get(item.id, 0),
                    "traits": item.traits.to_public(),
                    "payload": {
                        "emerged_at_world_age": item.emerged_at_world_age,
                        "chirality": item.chirality,
                        "heterochiral_load": item.heterochiral_load,
                    },
                }
                for item in state.species.values()
            ],
        )
    if state.populations:
        connection.execute(
            population_snapshots.insert(),
            [
                {
                    "universe_id": state.universe.id,
                    "tick": state.universe.tick,
                    "species_id": population.species_id,
                    "region_id": population.region_id,
                    "world_age": state.universe.age_years,
                    "population_count": population.population_count,
                    "energy_consumption": population.energy_consumption,
                    "growth_rate": population.growth_rate,
                    "migration_pressure": population.migration_pressure,
                    "payload": {},
                }
                for population in state.populations.values()
            ],
        )


def _max_suffix(values: Iterable[str]) -> int:
    maximum = 0
    for value in values:
        try:
            maximum = max(maximum, int(value.rsplit("-", 1)[1]))
        except (IndexError, ValueError):
            continue
    return maximum


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 4)


def _region_snapshot_totals(state: AlphaState) -> tuple[dict[str, int], dict[str, int]]:
    populations: dict[str, int] = {}
    species_ids: dict[str, set[str]] = {}
    for population in state.populations.values():
        if population.population_count <= 0:
            continue
        populations[population.region_id] = (
            populations.get(population.region_id, 0) + population.population_count
        )
        species_ids.setdefault(population.region_id, set()).add(population.species_id)
    return populations, {
        region_id: len(region_species)
        for region_id, region_species in species_ids.items()
    }


def _species_snapshot_totals(state: AlphaState) -> tuple[dict[str, int], dict[str, int]]:
    populations: dict[str, int] = {}
    region_ids: dict[str, set[str]] = {}
    for population in state.populations.values():
        if population.population_count <= 0:
            continue
        populations[population.species_id] = (
            populations.get(population.species_id, 0) + population.population_count
        )
        region_ids.setdefault(population.species_id, set()).add(population.region_id)
    return populations, {
        species_id: len(species_regions)
        for species_id, species_regions in region_ids.items()
    }
