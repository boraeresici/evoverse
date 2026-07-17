from __future__ import annotations

import os
from dataclasses import replace

from fastapi.testclient import TestClient

os.environ["EVOVERSE_PERSISTENCE"] = "memory"

import app.main as app_main
from app.main import app
from app.services import AlphaStore


client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["regions"] >= 100


def test_landing_contract() -> None:
    response = client.get("/universes/alpha/landing")

    assert response.status_code == 200
    payload = response.json()
    assert payload["universe"]["name"] == "Alpha"
    assert payload["universe"]["ageYears"] > 0
    assert payload["featuredEvents"]
    assert payload["chroniclePreview"]
    assert len(payload["regions"]) >= 100


def test_latest_snapshot_contract() -> None:
    response = client.get("/universes/alpha/snapshots/latest")

    assert response.status_code == 200
    payload = response.json()
    assert payload["universe"]["name"] == "Alpha"
    assert payload["snapshot"]["universeId"] == "alpha"
    assert payload["snapshot"]["tick"] >= 0
    assert payload["snapshot"]["worldAge"] == payload["universe"]["ageYears"]
    assert payload["snapshot"]["regionCount"] == payload["universe"]["regionCount"]
    assert payload["snapshot"]["speciesCount"] >= 1
    assert payload["snapshot"]["populationCount"] >= 0
    assert payload["snapshot"]["eventCount"] >= 0
    assert "stability_index" in payload["snapshot"]["payload"]


def test_snapshot_details_contract() -> None:
    latest = client.get("/universes/alpha/snapshots/latest").json()["snapshot"]
    response = client.get(f"/universes/alpha/snapshots/{latest['tick']}/details")

    assert response.status_code == 200
    payload = response.json()
    assert payload["snapshot"]["tick"] == latest["tick"]
    assert payload["coverage"]["regionSnapshots"] == payload["snapshot"]["regionCount"]
    assert payload["coverage"]["speciesSnapshots"] == payload["snapshot"]["speciesCount"]
    assert payload["coverage"]["populationSnapshots"] > 0
    assert payload["regions"][0]["regionId"].startswith("region-")
    assert payload["species"][0]["speciesId"].startswith("sp-")
    assert payload["populations"][0]["populationCount"] > 0


def test_dynamic_report_universe_contract() -> None:
    response = client.get("/universes/alpha/reports/dynamic?scope=universe&limit=3")

    assert response.status_code == 200
    payload = response.json()
    assert payload["model"] == "dynamic_report_v1"
    assert payload["scope"]["type"] == "universe"
    assert payload["series"]
    assert payload["baseline"]["metrics"]["populationCount"] >= 0
    assert payload["current"]["metrics"]["speciesCount"] >= 1
    assert "populationCount" in payload["delta"]
    assert payload["coverage"]["seriesCount"] == len(payload["series"])


def test_dynamic_report_region_contract() -> None:
    region_id = client.get("/universes/alpha/regions").json()["regions"][0]["id"]
    response = client.get(
        f"/universes/alpha/reports/dynamic?scope=region&regionId={region_id}"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["scope"]["type"] == "region"
    assert payload["scope"]["regionId"] == region_id
    assert {"energyLevel", "resourceDensity", "stability"}.issubset(
        payload["current"]["metrics"]
    )
    assert payload["current"]["metadata"]["regionId"] == region_id


def test_dynamic_report_requires_scope_entities() -> None:
    response = client.get("/universes/alpha/reports/dynamic?scope=species")

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "bad_request"
    assert payload["error"]["message"] == "speciesId is required for this report scope"


def test_snapshot_list_contract() -> None:
    response = client.get("/universes/alpha/snapshots?limit=1&offset=0")

    assert response.status_code == 200
    payload = response.json()
    assert payload["universe"]["name"] == "Alpha"
    assert len(payload["snapshots"]) == 1
    assert payload["snapshots"][0]["universeId"] == "alpha"
    assert payload["snapshots"][0]["worldAge"] == payload["universe"]["ageYears"]
    assert payload["filters"] == {"fromAge": None, "toAge": None}
    assert payload["pagination"]["limit"] == 1
    assert payload["pagination"]["offset"] == 0
    assert payload["pagination"]["total"] >= 1
    assert "hasMore" in payload["pagination"]


def test_snapshot_list_age_filter_contract() -> None:
    latest = client.get("/universes/alpha/snapshots/latest").json()["snapshot"]
    response = client.get(
        "/universes/alpha/snapshots"
        f"?fromAge={latest['worldAge']}&toAge={latest['worldAge']}"
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["snapshots"]) == 1
    assert payload["snapshots"][0]["worldAge"] == latest["worldAge"]
    assert payload["filters"] == {
        "fromAge": latest["worldAge"],
        "toAge": latest["worldAge"],
    }


def test_snapshot_list_rejects_invalid_age_range() -> None:
    response = client.get("/universes/alpha/snapshots?fromAge=20&toAge=10")

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "bad_request"
    assert payload["error"]["message"] == "fromAge must be less than or equal to toAge"


def test_chronicle_pagination_contract() -> None:
    response = client.get("/universes/alpha/chronicle?limit=3&offset=2")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["events"]) == 3
    assert payload["pagination"]["limit"] == 3
    assert payload["pagination"]["offset"] == 2
    assert "hasMore" in payload["pagination"]


def test_chronicle_events_expose_payload_schema_contract() -> None:
    response = client.get("/universes/alpha/chronicle?limit=1&offset=0")

    assert response.status_code == 200
    event = response.json()["events"][0]
    assert event["payload"]["schemaVersion"] == 1
    assert event["payload"]["schema"] == event["payloadSchema"]
    assert event["payload"]["eventType"] == event["eventType"]
    assert event["payloadSchemaVersion"] == 1


def test_local_admin_lock_via_flag() -> None:
    from app.services.alpha_store import AdminPermissionError

    locked = AlphaStore(seed=4211, boot_ticks=1, allow_local_admin=False)
    try:
        locked.ensure_admin_permission(actor_id="local-admin")
        raise AssertionError("local-admin should be denied when allow_local_admin is False")
    except AdminPermissionError:
        pass

    allowed = AlphaStore(seed=4211, boot_ticks=1, allow_local_admin=True)
    # Should not raise.
    allowed.ensure_admin_permission(actor_id="local-admin")


def test_event_stream_cursor_contract() -> None:
    local_store = AlphaStore(seed=4211, boot_ticks=1)
    initial = local_store.event_stream(limit=5)

    assert initial["model"] == "event_stream_v1"
    assert initial["events"] == []
    assert initial["cursor"]
    assert initial["missedCursor"] is False

    local_store.advance(ticks=160)
    updates = local_store.event_stream(last_event_id=initial["cursor"], limit=100)

    assert updates["model"] == "event_stream_v1"
    assert updates["events"]
    assert updates["events"][0]["payloadSchemaVersion"] == 1
    assert updates["cursor"] == updates["events"][-1]["id"]
    assert updates["lastEventId"] == initial["cursor"]
    assert updates["missedCursor"] is False


def test_observer_follows_and_notifications_contract() -> None:
    user_id = "observer-contract-user"
    chronicle = client.get("/universes/alpha/chronicle?limit=50").json()["events"]
    region_event = next(event for event in chronicle if event["regionId"])
    species_event = next(event for event in chronicle if event["speciesId"])

    region_follow = client.post(
        f"/me/follows/regions/{region_event['regionId']}",
        json={"userId": user_id},
    )
    species_follow = client.post(
        f"/me/follows/species/{species_event['speciesId']}",
        json={"userId": user_id},
    )
    duplicate_region_follow = client.post(
        f"/me/follows/regions/{region_event['regionId']}",
        json={"userId": user_id},
    )

    assert region_follow.status_code == 200
    assert species_follow.status_code == 200
    assert duplicate_region_follow.status_code == 200
    assert duplicate_region_follow.json()["counts"] == {
        "regions": 1,
        "species": 1,
        "total": 2,
    }

    follows = client.get(f"/me/follows?userId={user_id}")

    assert follows.status_code == 200
    assert follows.json()["model"] == "observer_follows_v1"
    assert follows.json()["counts"]["total"] == 2

    notifications = client.get(f"/me/notifications?userId={user_id}&limit=20")

    assert notifications.status_code == 200
    payload = notifications.json()
    assert payload["model"] == "observer_notifications_v1"
    assert payload["unreadCount"] >= 2
    assert any(
        notification["kind"] == "followed_region_event"
        and notification["event"]["id"] == region_event["id"]
        for notification in payload["notifications"]
    )
    assert any(
        notification["kind"] == "followed_species_event"
        and notification["event"]["id"] == species_event["id"]
        for notification in payload["notifications"]
    )

    notification_id = payload["notifications"][0]["id"]
    read = client.post(
        f"/me/notifications/{notification_id}/read",
        json={"userId": user_id},
    )
    unread = client.get(f"/me/notifications?userId={user_id}&unreadOnly=true")
    delete_follow = client.delete(
        f"/me/follows/regions/{region_event['regionId']}?userId={user_id}"
    )

    assert read.status_code == 200
    assert read.json()["notification"]["read"] is True
    assert notification_id not in {
        notification["id"] for notification in unread.json()["notifications"]
    }
    assert delete_follow.status_code == 200
    assert delete_follow.json()["counts"]["regions"] == 0


def test_observer_notifications_mark_all_read_contract() -> None:
    user_id = "observer-read-all-user"
    chronicle = client.get("/universes/alpha/chronicle?limit=50").json()["events"]
    region_event = next(event for event in chronicle if event["regionId"])
    species_event = next(event for event in chronicle if event["speciesId"])

    client.post(f"/me/follows/regions/{region_event['regionId']}", json={"userId": user_id})
    client.post(f"/me/follows/species/{species_event['speciesId']}", json={"userId": user_id})

    before = client.get(f"/me/notifications?userId={user_id}")
    assert before.status_code == 200
    assert before.json()["unreadCount"] >= 2

    read_all = client.post("/me/notifications/read-all", json={"userId": user_id})
    assert read_all.status_code == 200
    body = read_all.json()
    assert body["markedRead"] is True
    assert body["markedCount"] >= 2
    assert body["unreadCount"] == 0

    after = client.get(f"/me/notifications?userId={user_id}")
    assert after.json()["unreadCount"] == 0
    assert all(notification["read"] for notification in after.json()["notifications"])

    # Idempotent: a second call marks nothing new.
    repeat = client.post("/me/notifications/read-all", json={"userId": user_id})
    assert repeat.status_code == 200
    assert repeat.json()["markedCount"] == 0


def test_catalyst_action_notification_contract() -> None:
    user_id = "catalyst-notification-user"
    region_id = client.get("/universes/alpha/regions").json()["regions"][-1]["id"]
    role = client.post(
        f"/admin/catalyst/users/{user_id}/role",
        json={"role": "catalyst", "status": "active", "grantedBy": "local-admin"},
    )

    accepted = client.post(
        "/catalyst/actions",
        json={
            "regionId": region_id,
            "actionType": "resource_burst",
            "userId": user_id,
        },
    )
    notifications = client.get(f"/me/notifications?userId={user_id}&limit=20")
    actions = client.get(f"/me/catalyst/actions?userId={user_id}&limit=5")

    assert role.status_code == 200
    assert role.json()["capabilities"]["permission"]["canUseCatalyst"] is True
    assert accepted.status_code == 200
    assert accepted.json()["model"] == "catalyst_action_result_v1"
    assert accepted.json()["message"] == "Influence initiated"
    assert accepted.json()["tracking"]["id"] == accepted.json()["action"]["id"]
    assert accepted.json()["capabilities"]["quotas"]
    assert notifications.status_code == 200
    assert any(
        notification["kind"] == "catalyst_action"
        for notification in notifications.json()["notifications"]
    )
    assert actions.status_code == 200
    assert actions.json()["model"] == "catalyst_actions_v1"
    assert actions.json()["actions"][0]["id"] == accepted.json()["action"]["id"]


def test_catalyst_role_gate_rejects_guest_contract() -> None:
    user_id = "guest-catalyst-user"
    region_id = client.get("/universes/alpha/regions").json()["regions"][-2]["id"]

    status = client.get(f"/me/catalyst/status?userId={user_id}&regionId={region_id}")
    rejected = client.post(
        "/catalyst/actions",
        json={
            "regionId": region_id,
            "actionType": "energy_pulse",
            "userId": user_id,
        },
    )

    assert status.status_code == 200
    assert status.json()["model"] == "catalyst_capabilities_v1"
    assert status.json()["permission"]["canUseCatalyst"] is False
    assert rejected.status_code == 403
    assert rejected.json()["error"]["code"] == "forbidden"


def test_identity_context_contract() -> None:
    region_id = client.get("/universes/alpha/regions").json()["regions"][-3]["id"]

    response = client.get(f"/me/identity?regionId={region_id}")
    guest = client.get(
        "/me/identity?catalystUserId=identity-guest&adminActorId=identity-guest"
    )
    session_guest = client.get(
        "/me/identity?observerUserId=local-observer&catalystUserId=local-catalyst&adminActorId=local-admin",
        headers={"x-evoverse-user-id": "identity-session-guest"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["model"] == "identity_context_v1"
    assert payload["auth"] == {
        "provider": "local",
        "status": "deferred",
        "nextProvider": "google",
        "source": "session_headers_or_explicit_ids",
        "sessionStrategy": "local_bridge",
        "localFallback": True,
        "trustedHeaderRequired": False,
        "googleClientConfigured": False,
    }
    assert payload["users"]["observer"]["id"] == "local-observer"
    assert payload["users"]["catalyst"]["role"] == "catalyst"
    assert payload["users"]["admin"]["role"] == "admin"
    assert payload["capabilities"]["observer"]["canFollow"] is True
    assert payload["capabilities"]["catalyst"]["permission"]["canUseCatalyst"] is True
    assert payload["capabilities"]["catalyst"]["regionId"] == region_id
    assert payload["capabilities"]["admin"]["canUseAdmin"] is True
    assert payload["roleGate"]["catalystAccess"] == "invite_or_role_gate"
    assert payload["roleGate"]["subscription"] == "deferred"

    assert guest.status_code == 200
    guest_payload = guest.json()
    assert guest_payload["users"]["catalyst"]["status"] == "guest"
    assert guest_payload["capabilities"]["catalyst"]["permission"] == {
        "canUseCatalyst": False,
        "reason": "catalyst_role_required",
    }
    assert guest_payload["capabilities"]["admin"] == {
        "canUseAdmin": False,
        "reason": "admin_role_required",
    }
    assert session_guest.status_code == 200
    session_payload = session_guest.json()
    assert session_payload["users"]["observer"]["id"] == "identity-session-guest"
    assert session_payload["users"]["catalyst"]["id"] == "identity-session-guest"
    assert session_payload["users"]["admin"]["id"] == "identity-session-guest"
    assert session_payload["capabilities"]["admin"]["canUseAdmin"] is False


def test_identity_requires_session_when_local_fallback_is_disabled(monkeypatch) -> None:
    monkeypatch.setattr(
        app_main,
        "settings",
        replace(app_main.settings, auth_allow_local_fallback=False),
    )

    missing_session = client.get(
        "/me/identity?observerUserId=local-observer&catalystUserId=local-catalyst&adminActorId=local-admin"
    )
    with_session = client.get(
        "/me/identity?observerUserId=ignored&catalystUserId=ignored&adminActorId=ignored",
        headers={"x-evoverse-user-id": "local-admin"},
    )

    assert missing_session.status_code == 401
    assert missing_session.json()["error"]["code"] == "unauthorized"
    assert with_session.status_code == 200
    assert with_session.json()["users"]["observer"]["id"] == "local-admin"
    assert with_session.json()["users"]["admin"]["id"] == "local-admin"


def test_identity_requires_trusted_auth_secret_when_configured(monkeypatch) -> None:
    monkeypatch.setattr(
        app_main,
        "settings",
        replace(
            app_main.settings,
            auth_allow_local_fallback=False,
            auth_trusted_header_secret="session-secret",
        ),
    )

    untrusted_session = client.get(
        "/me/identity",
        headers={"x-evoverse-user-id": "local-admin"},
    )
    trusted_session = client.get(
        "/me/identity",
        headers={
            "x-evoverse-user-id": "local-admin",
            "x-evoverse-auth-secret": "session-secret",
        },
    )

    assert untrusted_session.status_code == 401
    assert untrusted_session.json()["error"]["code"] == "unauthorized"
    assert trusted_session.status_code == 200
    assert trusted_session.json()["users"]["admin"]["id"] == "local-admin"


def test_region_and_species_drilldown_contracts() -> None:
    landing = client.get("/universes/alpha/landing").json()
    region_id = landing["regions"][0]["id"]
    species_id = landing["species"][0]["id"]

    region_response = client.get(f"/regions/{region_id}")
    species_response = client.get(f"/species/{species_id}")

    assert region_response.status_code == 200
    assert species_response.status_code == 200
    assert "events" in region_response.json()
    assert "forecast" in species_response.json()["species"]


def test_species_forecast_endpoint_contract() -> None:
    species_id = client.get("/species").json()["species"][0]["id"]
    detail = client.get(f"/species/{species_id}").json()
    response = client.get(f"/species/{species_id}/forecast")

    assert response.status_code == 200
    payload = response.json()
    assert payload["universe"]["name"] == "Alpha"
    assert payload["species"]["id"] == species_id
    assert payload["forecast"] == detail["species"]["forecast"]
    assert payload["model"] == "forecast_lite_v1"
    assert payload["generatedAtWorldAge"] == payload["universe"]["ageYears"]
    assert set(payload["forecast"]) == {
        "extinctionRisk",
        "dominanceProbability",
        "expansionPressure",
        "mutationVolatility",
    }


def test_species_forecast_not_found_contract() -> None:
    response = client.get("/species/species-999/forecast")

    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["code"] == "not_found"
    assert payload["error"]["message"] == "Species not found"


def test_region_and_species_event_pagination_contracts() -> None:
    landing = client.get("/universes/alpha/landing").json()
    # Some event types (e.g. era_advanced) carry no region, so pick the first
    # featured event that has one; fall back to a region that always seeds.
    region_id = next(
        (event["regionId"] for event in landing["featuredEvents"] if event["regionId"]),
        "region-001",
    )
    species_id = client.get("/species").json()["species"][0]["id"]

    region_events = client.get(f"/regions/{region_id}/events?limit=2&offset=0")
    species_events = client.get(f"/species/{species_id}/events?limit=2&offset=0")

    assert region_events.status_code == 200
    assert species_events.status_code == 200
    assert region_events.json()["pagination"]["limit"] == 2
    assert species_events.json()["pagination"]["limit"] == 2


def test_admin_simulation_health_contract() -> None:
    response = client.get("/admin/simulation/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["tick"] >= 0
    assert payload["eventCounts"]
    assert payload["worker"] is None


def test_admin_simulation_controls_and_batch_contract() -> None:
    controls = client.get("/admin/simulation/controls")
    before_tick = controls.json()["universe"]["tick"]

    batch = client.post(
        "/admin/simulation/batches",
        json={
            "ticks": 2,
            "actorId": "local-admin",
            "reason": "Contract batch tick",
        },
    )
    runs = client.get("/admin/simulation/runs?limit=1")

    assert controls.status_code == 200
    controls_payload = controls.json()
    assert controls_payload["model"] == "admin_simulation_controls_v1"
    assert controls_payload["controls"]["batchTick"]["maxTicks"] == 500
    assert controls_payload["controls"]["seedReset"]["requiresConfirmReset"] is True
    assert controls_payload["debug"]["visibility"] == "admin_only"
    assert batch.status_code == 200
    batch_payload = batch.json()
    assert batch_payload["model"] == "admin_simulation_batch_v1"
    assert batch_payload["run"]["actionType"] == "batch_tick"
    assert batch_payload["run"]["requestedTicks"] == 2
    assert batch_payload["before"]["tick"] == before_tick
    assert batch_payload["after"]["tick"] == before_tick + 2
    assert runs.status_code == 200
    assert runs.json()["runs"][0]["id"] == batch_payload["run"]["id"]


def test_admin_simulation_reset_contract() -> None:
    rejected = client.post(
        "/admin/simulation/reset",
        json={"actorId": "local-admin", "bootTicks": 2},
    )
    accepted = client.post(
        "/admin/simulation/reset",
        json={
            "actorId": "local-admin",
            "reason": "Contract reset",
            "seed": 4211,
            "bootTicks": 2,
            "preserveUserState": True,
            "confirmReset": True,
        },
    )

    assert rejected.status_code == 400
    assert rejected.json()["error"]["message"] == "confirmReset must be true"
    assert accepted.status_code == 200
    payload = accepted.json()
    assert payload["model"] == "admin_simulation_reset_v1"
    assert payload["run"]["actionType"] == "seed_reset"
    assert payload["run"]["requestedTicks"] == 2
    assert payload["after"]["tick"] == 2
    assert payload["controls"]["debug"]["seed"] == 4211


def test_admin_simulation_health_operations_contract() -> None:
    response = client.get("/admin/simulation/health")

    assert response.status_code == 200
    operations = response.json()["operations"]
    assert operations["env"] == "local"
    assert operations["destructiveOpsAllowed"] is True
    assert operations["workerStaleThresholdSeconds"] == 30.0
    assert operations["workerStale"] is False
    # Memory-backed test store has no worker heartbeat.
    assert operations["workerState"] == "unknown"


def test_admin_simulation_reset_blocked_when_destructive_ops_disabled(monkeypatch) -> None:
    monkeypatch.setattr(
        app_main,
        "settings",
        replace(app_main.settings, allow_destructive_ops=False),
    )

    response = client.post(
        "/admin/simulation/reset",
        json={"actorId": "local-admin", "confirmReset": True, "bootTicks": 2},
    )

    assert response.status_code == 403
    assert "disabled" in response.json()["error"]["message"].lower()


def test_admin_write_gate_rejects_guest_session_contract() -> None:
    batch = client.post(
        "/admin/simulation/batches",
        headers={"x-evoverse-user-id": "guest-admin"},
        json={"ticks": 1, "actorId": "local-admin"},
    )
    role_grant = client.post(
        "/admin/catalyst/users/session-guest-catalyst/role",
        headers={"x-evoverse-user-id": "guest-admin"},
        json={"role": "catalyst", "status": "active", "grantedBy": "local-admin"},
    )
    rules = client.post(
        "/admin/simulation/rules/validate",
        headers={"x-evoverse-user-id": "guest-admin"},
        json={"actorId": "local-admin", "rules": {"population": {"growthFactor": 0.12}}},
    )

    assert batch.status_code == 403
    assert batch.json()["error"]["code"] == "forbidden"
    assert role_grant.status_code == 403
    assert role_grant.json()["error"]["code"] == "forbidden"
    assert rules.status_code == 403
    assert rules.json()["error"]["message"] == "Admin role is required for guest-admin"


def test_observability_and_analytics_contract() -> None:
    landing = client.get("/universes/alpha/landing")
    region_id = landing.json()["regions"][0]["id"]
    region_detail = client.get(f"/regions/{region_id}")
    replay = client.post(
        "/analytics/events",
        json={
            "eventName": "replay_interaction",
            "sessionId": "contract-session",
            "subjectType": "universe",
            "subjectId": "alpha",
            "source": "client",
            "metadata": {"control": "step_forward"},
        },
    )
    missing = client.get("/regions/region-999")

    summary = client.get("/admin/observability/summary")
    requests = client.get("/admin/observability/requests?limit=5")
    errors = client.get("/admin/observability/errors?limit=5")
    analytics = client.get("/admin/analytics/events?limit=10")

    assert landing.status_code == 200
    assert region_detail.status_code == 200
    assert replay.status_code == 200
    assert replay.json()["model"] == "product_analytics_event_v1"
    assert missing.status_code == 404
    assert summary.status_code == 200
    summary_payload = summary.json()
    assert summary_payload["model"] == "observability_summary_v1"
    assert summary_payload["requests"]["total"] >= 4
    assert summary_payload["errors"]["total"] >= 1
    assert summary_payload["analytics"]["events"]["landing_view"] >= 1
    assert summary_payload["analytics"]["events"]["detail_view"] >= 1
    assert summary_payload["analytics"]["replayInteractions"] >= 1
    assert requests.status_code == 200
    assert requests.json()["model"] == "api_request_logs_v1"
    assert errors.status_code == 200
    assert errors.json()["model"] == "api_error_logs_v1"
    assert any(error["statusCode"] == 404 for error in errors.json()["errors"])
    assert analytics.status_code == 200
    assert analytics.json()["model"] == "product_analytics_events_v1"


def test_admin_simulation_rules_contract() -> None:
    response = client.get("/admin/simulation/rules")

    assert response.status_code == 200
    payload = response.json()
    assert payload["model"] == "simulation_rules_v1"
    assert payload["mode"] == "editable"
    assert payload["source"] == "backend/app/simulation/rules.py"
    assert payload["rules"]["catalyst"]["dailyLimits"]["energy_pulse"] == 3
    assert payload["rules"]["catalyst"]["dailyLimits"]["mutation_pulse"] == 1
    assert payload["rules"]["catalyst"]["dailyLimits"]["resource_burst"] == 1
    assert payload["rules"]["catalyst"]["effectTicks"] == 8
    assert payload["rules"]["population"]["growthFactor"] == 0.14
    assert payload["rules"]["population"]["densityPressureCap"] == 0.16
    assert payload["rules"]["region"]["energyEquilibrium"] == 0.56
    assert payload["rules"]["region"]["recoveryStabilityThreshold"] == 0.34
    assert payload["rules"]["region"]["collapseStabilityThreshold"] == 0.16
    assert payload["rules"]["region"]["collapseResourceThreshold"] == 0.18
    assert payload["rules"]["speciation"]["candidateMinPopulation"] == 1800
    assert payload["rules"]["speciation"]["intervalTicks"] == 149
    assert payload["governance"]["validation"] == "enabled"
    assert payload["governance"]["auditLog"] == "enabled"
    assert payload["governance"]["rollback"] == "enabled"
    assert payload["governance"]["writeSurface"] == "api_and_admin_ui"
    assert payload["governance"]["uiEditable"] is True


def test_admin_simulation_rules_validate_contract() -> None:
    response = client.post(
        "/admin/simulation/rules/validate",
        json={
            "actorId": "local-admin",
            "reason": "Validate growth tuning",
            "rules": {"population": {"growthFactor": 0.12}},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["valid"] is True
    assert payload["rules"]["population"]["growthFactor"] == 0.12
    assert payload["audit"]["actionType"] == "validate"
    assert payload["audit"]["status"] == "accepted"
    assert payload["reloadStrategy"]["api"]["status"] == "not_applied"


def test_admin_simulation_rules_validate_rejects_invalid_contract() -> None:
    response = client.post(
        "/admin/simulation/rules/validate",
        json={
            "actorId": "local-admin",
            "rules": {
                "population": {"growthFactor": 1.4},
                "unknown": {"value": 1},
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["valid"] is False
    assert payload["rules"] is None
    assert payload["audit"]["status"] == "rejected"
    assert {error["path"] for error in payload["errors"]} == {
        "population.growthFactor",
        "unknown",
    }


def test_admin_simulation_rules_audit_contract() -> None:
    client.post(
        "/admin/simulation/rules/validate",
        json={
            "actorId": "local-admin",
            "rules": {"speciation": {"intervalTicks": 157}},
        },
    )
    response = client.get("/admin/simulation/rules/audit?limit=5&offset=0")

    assert response.status_code == 200
    payload = response.json()
    assert payload["pagination"]["limit"] == 5
    assert payload["pagination"]["total"] >= 1
    assert payload["audit"][0]["actionType"] == "validate"


def test_not_found_error_contract() -> None:
    response = client.get("/regions/region-999")

    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["code"] == "not_found"
    assert payload["error"]["message"] == "Region not found"
    assert payload["error"]["status"] == 404


def test_validation_error_contract() -> None:
    response = client.get("/universes/alpha/chronicle?limit=0")

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["message"] == "Request validation failed"
    assert payload["error"]["status"] == 422
    assert payload["error"]["details"]


def test_bad_request_error_contract() -> None:
    response = client.post(
        "/catalyst/actions",
        json={
            "regionId": "region-001",
            "actionType": "unknown_pulse",
            "userId": "error-contract-user",
        },
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "bad_request"
    assert payload["error"]["status"] == 400


def test_diagnostics_contract() -> None:
    client = TestClient(app)

    response = client.get("/universes/alpha/diagnostics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["model"] == "diagnostics_v1"
    assert payload["universe"]["seed"] > 0
    assert set(payload["correlation"]) >= {"stability", "energy_level"}

    stability = payload["correlation"]["stability"]
    # Pair counts ride with the curve: they are what separates the measured span
    # from the tail, where a handful of pairs can push C(r) past C(0) = 1.
    assert [r for r, _ in stability["curve"]] == [r for r, _ in stability["pairs"]]
    assert "xiFloored" in stability and "degenerate" in stability
    assert "saturated" not in stability

    # The scan is never computed in-request (it replays a seed ensemble and takes
    # minutes); it is whatever the worker parked, and null is a real state a fresh
    # universe must be able to report.
    assert "scaleFree" in payload
    assert payload["scaleFree"] is None or "scanTicks" in payload["scaleFree"]


def test_diagnostics_gates_trigger_lift_on_support() -> None:
    client = TestClient(app)

    families = client.get("/universes/alpha/diagnostics").json()["triggers"]["families"]

    for name, family in families.items():
        # Nothing below the support gate may reach a consumer: under it, lift is
        # arithmetic on singletons rather than an association.
        for row in family["reportable"]:
            assert row["support"] >= 5, name
        # The page shows its own reasoning, so the raw shape stays visible.
        assert family["singletonRows"] <= family["rows"]
