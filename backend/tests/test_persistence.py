from __future__ import annotations

from dataclasses import replace

import pytest
from sqlalchemy import update

from app.domain import CatalystActionType
from app.persistence import AlphaStateConflictError, AlphaStateRepository
from app.persistence.schema import events as events_table
from app.services import AlphaStore
from app.services.alpha_store import AdminPermissionError, CatalystCooldownError, CatalystLimitError
from app.simulation import DEFAULT_SIMULATION_RULES, SimulationEngine, seed_alpha


def test_repository_round_trips_alpha_state(tmp_path) -> None:
    repository = AlphaStateRepository(
        f"sqlite+pysqlite:///{tmp_path / 'alpha.db'}",
        create_schema=True,
    )
    state = seed_alpha(seed=4211)
    SimulationEngine(seed=4211).advance(state, ticks=24)

    repository.save_alpha(state)
    loaded = repository.load_alpha(seed=4211)

    assert loaded is not None
    assert loaded.universe.age_years == state.universe.age_years
    assert loaded.universe.tick == state.universe.tick
    assert len(loaded.regions) == len(state.regions)
    assert len(loaded.species) == len(state.species)
    assert len(loaded.events) == len(state.events)
    assert loaded.next_event_index == state.next_event_index
    assert loaded.next_species_index == state.next_species_index
    assert repository.snapshot_count() == 1


def test_repository_writes_entity_snapshot_details(tmp_path) -> None:
    repository = AlphaStateRepository(
        f"sqlite+pysqlite:///{tmp_path / 'alpha.db'}",
        create_schema=True,
    )
    state = seed_alpha(seed=4211)
    SimulationEngine(seed=4211).advance(state, ticks=12)

    repository.save_alpha(state)
    details = repository.snapshot_details(state.universe.tick)

    assert details is not None
    assert len(details["regions"]) == len(state.regions)
    assert len(details["species"]) == len(state.species)
    assert len(details["populations"]) == len(state.populations)
    assert details["snapshot"]["payload"]["snapshot_model"] == "entity_snapshots_v1"
    assert repository.snapshot_detail_counts(state.universe.tick) == {
        "region_snapshots": len(state.regions),
        "species_snapshots": len(state.species),
        "population_snapshots": len(state.populations),
    }


def test_db_backed_store_persists_advancement(tmp_path) -> None:
    repository = AlphaStateRepository(
        f"sqlite+pysqlite:///{tmp_path / 'alpha.db'}",
        create_schema=True,
    )
    first_store = AlphaStore(
        seed=4211,
        boot_ticks=12,
        repository=repository,
        refresh_on_read=False,
    )
    initial_age = first_store.health()["ageYears"]

    first_store.advance(ticks=7)
    second_store = AlphaStore(
        seed=4211,
        boot_ticks=96,
        repository=repository,
        refresh_on_read=False,
    )

    assert second_store.health()["persistence"] == "sqlite"
    assert second_store.health()["ageYears"] == initial_age + 7
    assert repository.snapshot_count() == 2


def test_store_bootstraps_auth_role_invites() -> None:
    store = AlphaStore(
        seed=4211,
        boot_ticks=1,
        bootstrap_admins=("google-admin@example.com",),
        bootstrap_catalysts=("google-catalyst@example.com",),
    )

    identity = store.identity_context(
        admin_actor_id="google-admin@example.com",
        catalyst_user_id="google-catalyst@example.com",
    )

    assert identity["users"]["admin"]["role"] == "admin"
    assert identity["capabilities"]["admin"]["canUseAdmin"] is True
    assert identity["users"]["catalyst"]["role"] == "catalyst"
    assert identity["capabilities"]["catalyst"]["permission"]["canUseCatalyst"] is True
    assert store.ensure_admin_permission(actor_id="google-admin@example.com")["role"] == "admin"
    with pytest.raises(AdminPermissionError):
        store.ensure_admin_permission(actor_id="google-catalyst@example.com")


def test_repository_lists_snapshots_latest_first_with_filters(tmp_path) -> None:
    repository = AlphaStateRepository(
        f"sqlite+pysqlite:///{tmp_path / 'alpha.db'}",
        create_schema=True,
    )
    store = AlphaStore(
        seed=4211,
        boot_ticks=5,
        repository=repository,
        refresh_on_read=False,
    )
    store.advance(ticks=2)
    store.advance(ticks=3)

    page = repository.snapshots(limit=2, offset=0)
    ticks = [int(snapshot["tick"]) for snapshot in page["items"]]

    assert page["total"] == 3
    assert ticks == sorted(ticks, reverse=True)
    assert len(page["items"]) == 2

    next_page = repository.snapshots(limit=2, offset=2)
    assert len(next_page["items"]) == 1

    from_age = int(page["items"][1]["world_age"])
    to_age = int(page["items"][0]["world_age"])
    filtered = repository.snapshots(
        limit=10,
        offset=0,
        from_world_age=from_age,
        to_world_age=to_age,
    )

    assert filtered["total"] == 2
    assert all(
        from_age <= int(snapshot["world_age"]) <= to_age
        for snapshot in filtered["items"]
    )


def test_repository_detects_stale_tick_save(tmp_path) -> None:
    repository = AlphaStateRepository(
        f"sqlite+pysqlite:///{tmp_path / 'alpha.db'}",
        create_schema=True,
    )
    repository.save_alpha(seed_alpha(seed=4211))
    first = repository.load_alpha(seed=4211)
    second = repository.load_alpha(seed=4211)

    assert first is not None
    assert second is not None
    base_tick = first.universe.tick
    SimulationEngine(seed=4211).advance(first, ticks=1)
    repository.save_alpha(first, expected_tick=base_tick)
    SimulationEngine(seed=4211).advance(second, ticks=1)

    with pytest.raises(AlphaStateConflictError):
        repository.save_alpha(second, expected_tick=base_tick)


def test_event_store_is_append_only_across_current_snapshot_saves(tmp_path) -> None:
    repository = AlphaStateRepository(
        f"sqlite+pysqlite:///{tmp_path / 'alpha.db'}",
        create_schema=True,
    )
    state = seed_alpha(seed=4211)
    SimulationEngine(seed=4211).advance(state, ticks=40)
    repository.save_alpha(state)
    original_event_count = len(state.events)

    loaded = repository.load_alpha(seed=4211)
    assert loaded is not None
    base_tick = loaded.universe.tick
    loaded.events = loaded.events[-1:]
    loaded.universe.tick += 1
    loaded.universe.age_years += 1
    repository.save_alpha(loaded, expected_tick=base_tick)

    reloaded = repository.load_alpha(seed=4211)
    assert reloaded is not None
    assert len(reloaded.events) == original_event_count
    assert reloaded.next_event_index == state.next_event_index


def test_events_page_keyset_paginates_the_full_log(tmp_path, monkeypatch) -> None:
    import app.persistence.repository as repo

    # Force the in-memory hydration cap low to prove the keyset feed reads the
    # full DB history, not just the loaded slice.
    monkeypatch.setattr(repo, "MAX_LOADED_EVENTS", 20)
    repository = AlphaStateRepository(
        f"sqlite+pysqlite:///{tmp_path / 'alpha.db'}",
        create_schema=True,
    )
    state = seed_alpha(seed=4211)
    SimulationEngine(seed=4211).advance(state, ticks=400)
    repository.save_alpha(state)

    all_ids_newest_first = [event.id for event in reversed(state.events)]
    assert len(all_ids_newest_first) > 20  # exceeds the in-memory cap
    assert len(repository.load_alpha(seed=4211).events) == 20  # load respects cap

    seen: list[str] = []
    cursor = None
    pages = 0
    while True:
        page = repository.events_page(limit=7, cursor=cursor)
        seen.extend(event.id for event in page["items"])
        assert page["pagination"]["total"] == len(all_ids_newest_first)
        cursor = page["pagination"]["nextCursor"]
        pages += 1
        assert pages < 1000  # guard against a non-advancing cursor
        if cursor is None:
            break

    assert seen == all_ids_newest_first  # gapless, newest-first, no duplicates
    assert len(set(seen)) == len(seen)
    assert page["pagination"]["hasMore"] is False


def test_events_page_filters_by_entity_and_supports_offset(tmp_path) -> None:
    repository = AlphaStateRepository(
        f"sqlite+pysqlite:///{tmp_path / 'alpha.db'}",
        create_schema=True,
    )
    state = seed_alpha(seed=4211)
    SimulationEngine(seed=4211).advance(state, ticks=200)
    repository.save_alpha(state)

    region_id = "region-001"
    expected = [
        event.id for event in reversed(state.events) if event.region_id == region_id
    ]
    page = repository.events_page(limit=100, region_id=region_id)
    assert [event.id for event in page["items"]] == expected
    assert page["pagination"]["total"] == len(expected)
    assert all(event.region_id == region_id for event in page["items"])

    # Offset path (no cursor) still walks the full log, in the same order.
    first = repository.events_page(limit=5, offset=0)
    second = repository.events_page(limit=5, offset=5)
    combined = [event.id for event in first["items"]] + [
        event.id for event in second["items"]
    ]
    assert combined == [event.id for event in reversed(state.events)][:10]
    assert first["pagination"]["nextOffset"] == 5


def test_repository_normalizes_legacy_event_payloads_on_load(tmp_path) -> None:
    repository = AlphaStateRepository(
        f"sqlite+pysqlite:///{tmp_path / 'alpha.db'}",
        create_schema=True,
    )
    state = seed_alpha(seed=4211)
    repository.save_alpha(state)
    event = state.events[0]
    legacy_payload = {
        key: value
        for key, value in event.payload.items()
        if key not in {"schemaVersion", "schema", "eventType"}
    }
    with repository.engine.begin() as connection:
        connection.execute(
            update(events_table)
            .where(events_table.c.id == event.id)
            .values(payload=legacy_payload)
        )

    loaded = repository.load_alpha(seed=4211)

    assert loaded is not None
    assert loaded.events[0].payload["schemaVersion"] == 1
    assert loaded.events[0].payload["schema"] == "event_payload.species_emerged.v1"
    assert loaded.events[0].payload["eventType"] == "species_emerged"


def test_worker_heartbeat_round_trip(tmp_path) -> None:
    repository = AlphaStateRepository(
        f"sqlite+pysqlite:///{tmp_path / 'alpha.db'}",
        create_schema=True,
    )
    repository.save_alpha(seed_alpha(seed=4211))

    repository.record_worker_heartbeat(
        worker_id="test-worker",
        universe_id="alpha",
        status="running",
        last_tick=12,
        last_world_age=4223,
        last_step=3,
    )
    heartbeat = repository.latest_worker_heartbeat()

    assert heartbeat is not None
    assert heartbeat["worker_id"] == "test-worker"
    assert heartbeat["status"] == "running"
    assert int(heartbeat["last_tick"]) == 12


def test_observability_and_analytics_round_trip(tmp_path) -> None:
    repository = AlphaStateRepository(
        f"sqlite+pysqlite:///{tmp_path / 'alpha.db'}",
        create_schema=True,
    )
    repository.save_alpha(seed_alpha(seed=4211))

    request = repository.record_api_request_log(
        method="GET",
        path="/universes/alpha/landing",
        route="/universes/alpha/landing",
        status_code=200,
        duration_ms=12.5,
        request_id="req-test",
        client_host="testclient",
    )
    error = repository.record_api_error_log(
        method="GET",
        path="/regions/missing",
        route="/regions/{region_id}",
        status_code=404,
        error_code="not_found",
        message="Region not found",
        request_id="req-error",
    )
    worker_event = repository.record_worker_run_event(
        worker_id="worker-1",
        universe_id="alpha",
        event_type="start",
        status="running",
    )
    repository.record_product_analytics_event(
        universe_id="alpha",
        event_name="landing_view",
        source="server",
    )
    repository.record_product_analytics_event(
        universe_id="alpha",
        event_name="detail_view",
        subject_type="region",
        subject_id="region-001",
        source="server",
    )

    requests = repository.api_request_logs_page()
    errors = repository.api_error_logs_page()
    worker_events = repository.worker_run_events_page()
    analytics = repository.product_analytics_events_page()

    assert requests["items"][0]["id"] == request["id"]
    assert repository.api_request_summary()["total"] == 1
    assert errors["items"][0]["id"] == error["id"]
    assert repository.api_error_summary()["errorCodes"] == {"not_found": 1}
    assert worker_events["items"][0]["id"] == worker_event["id"]
    assert repository.worker_run_summary()["starts"] == 1
    assert analytics["total"] == 2
    assert repository.product_analytics_summary()["landingToDetailRate"] == 1.0


def test_observer_follow_and_notification_read_round_trip(tmp_path) -> None:
    repository = AlphaStateRepository(
        f"sqlite+pysqlite:///{tmp_path / 'alpha.db'}",
        create_schema=True,
    )
    repository.save_alpha(seed_alpha(seed=4211))

    follow = repository.save_observer_follow(
        user_id="observer-1",
        entity_type="region",
        entity_id="region-001",
    )
    duplicate = repository.save_observer_follow(
        user_id="observer-1",
        entity_type="region",
        entity_id="region-001",
    )
    follows = repository.observer_follows(user_id="observer-1")

    assert follow["id"] == duplicate["id"]
    assert len(follows) == 1
    assert follows[0]["entity_id"] == "region-001"

    read = repository.record_notification_read(
        user_id="observer-1",
        notification_id="notif-evt-000001-followed_region_event-region-001",
    )
    reads = repository.notification_reads(user_id="observer-1")

    assert reads[read["notification_id"]]["user_id"] == "observer-1"
    assert repository.delete_observer_follow(
        user_id="observer-1",
        entity_type="region",
        entity_id="region-001",
    ) is True
    assert repository.observer_follows(user_id="observer-1") == []


def test_catalyst_region_cooldown_blocks_repeat_region_action(tmp_path) -> None:
    repository = AlphaStateRepository(
        f"sqlite+pysqlite:///{tmp_path / 'alpha.db'}",
        create_schema=True,
    )
    store = AlphaStore(
        seed=4211,
        boot_ticks=12,
        repository=repository,
        refresh_on_read=False,
    )
    store.grant_catalyst_role(user_id="cooldown-user", granted_by="test-admin")

    accepted = store.catalyst_action(
        "region-001",
        "energy_pulse",
        user_id="cooldown-user",
    )

    assert accepted["accepted"] is True
    with pytest.raises(CatalystCooldownError):
        store.catalyst_action(
            "region-001",
            "energy_pulse",
            user_id="cooldown-user",
        )


def test_catalyst_daily_limit_is_persisted_per_user_and_action(tmp_path) -> None:
    repository = AlphaStateRepository(
        f"sqlite+pysqlite:///{tmp_path / 'alpha.db'}",
        create_schema=True,
    )
    store = AlphaStore(
        seed=4211,
        boot_ticks=12,
        repository=repository,
        refresh_on_read=False,
    )
    user_id = "quota-user"
    store.grant_catalyst_role(user_id=user_id, granted_by="test-admin")

    for region_id in ["region-001", "region-002", "region-003"]:
        store.catalyst_action(region_id, "energy_pulse", user_id=user_id)

    with pytest.raises(CatalystLimitError):
        store.catalyst_action("region-004", "energy_pulse", user_id=user_id)

    reloaded_store = AlphaStore(
        seed=4211,
        boot_ticks=12,
        repository=repository,
        refresh_on_read=False,
    )
    with pytest.raises(CatalystLimitError):
        reloaded_store.catalyst_action("region-005", "energy_pulse", user_id=user_id)


def test_catalyst_daily_limit_uses_rules_config(tmp_path) -> None:
    repository = AlphaStateRepository(
        f"sqlite+pysqlite:///{tmp_path / 'alpha.db'}",
        create_schema=True,
    )
    rules = replace(
        DEFAULT_SIMULATION_RULES,
        catalyst=replace(
            DEFAULT_SIMULATION_RULES.catalyst,
            daily_limits={
                **DEFAULT_SIMULATION_RULES.catalyst.daily_limits,
                CatalystActionType.ENERGY_PULSE: 1,
            },
        ),
    )
    store = AlphaStore(
        seed=4211,
        boot_ticks=12,
        repository=repository,
        refresh_on_read=False,
        rules=rules,
    )
    user_id = "rules-quota-user"
    store.grant_catalyst_role(user_id=user_id, granted_by="test-admin")

    store.catalyst_action("region-001", "energy_pulse", user_id=user_id)

    with pytest.raises(CatalystLimitError):
        store.catalyst_action("region-002", "energy_pulse", user_id=user_id)
