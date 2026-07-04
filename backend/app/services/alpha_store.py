from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from threading import RLock
from uuid import uuid4

from app.domain import CatalystActionType, EventType
from app.persistence import AlphaStateConflictError, AlphaStateRepository
from app.services.serializers import (
    serialize_event,
    serialize_population,
    serialize_region,
    serialize_species,
    serialize_species_forecast,
    serialize_universe,
)
from app.simulation import SimulationEngine, seed_alpha
from app.simulation.rule_config import (
    reload_strategy,
    rules_from_public,
    rules_hash,
    rules_to_public,
    validate_rules_update,
)
from app.simulation.rules import DEFAULT_SIMULATION_RULES, SimulationRules


class CatalystLimitError(ValueError):
    pass


class CatalystCooldownError(ValueError):
    pass


class CatalystPermissionError(ValueError):
    pass


class AdminPermissionError(ValueError):
    pass


class RuleConfigValidationError(ValueError):
    def __init__(self, response: dict) -> None:
        self.response = response
        super().__init__("Simulation rules validation failed")


class RuleConfigRollbackError(ValueError):
    pass


LOCAL_OBSERVER_USER_ID = "local-observer"
LOCAL_CATALYST_USER_ID = "local-catalyst"
LOCAL_ADMIN_ACTOR_ID = "local-admin"

CATALYST_ROLES = {"admin", "catalyst"}
CATALYST_ROLE_STATUSES = {"active", "revoked"}


class AlphaStore:
    def __init__(
        self,
        seed: int = 4211,
        boot_ticks: int = 96,
        *,
        repository: AlphaStateRepository | None = None,
        refresh_on_read: bool = False,
        rules: SimulationRules | None = None,
        auth_provider: str = "local",
        auth_allow_local_fallback: bool = True,
        auth_trusted_header_required: bool = False,
        auth_google_client_id: str | None = None,
        bootstrap_admins: tuple[str, ...] | None = None,
        bootstrap_catalysts: tuple[str, ...] | None = None,
        allow_local_admin: bool = True,
    ) -> None:
        self._lock = RLock()
        self._seed = seed
        self._boot_ticks = boot_ticks
        self._repository = repository
        self._refresh_on_read = refresh_on_read
        self._auth_provider = auth_provider
        self._auth_allow_local_fallback = auth_allow_local_fallback
        self._auth_trusted_header_required = auth_trusted_header_required
        self._auth_google_client_id = auth_google_client_id
        # When local admin is disabled (e.g. a public demo), no id is bootstrapped
        # as admin, so the local fallback identity has no admin rights.
        self._bootstrap_admins = _bootstrap_ids(
            bootstrap_admins,
            fallback=LOCAL_ADMIN_ACTOR_ID if allow_local_admin else None,
        )
        self._bootstrap_catalysts = _bootstrap_ids(bootstrap_catalysts, fallback=LOCAL_CATALYST_USER_ID)
        self._memory_catalyst_counts: dict[tuple[str, str, str], int] = {}
        self._memory_catalyst_action_logs: dict[str, dict] = {}
        self._memory_catalyst_roles: dict[tuple[str, str], dict] = {}
        self._memory_follows: dict[tuple[str, str, str], dict] = {}
        self._memory_notification_reads: dict[tuple[str, str], dict] = {}
        self._memory_rule_configs: list[dict] = []
        self._memory_rule_audit: list[dict] = []
        self._memory_admin_runs: list[dict] = []
        self._memory_api_requests: list[dict] = []
        self._memory_api_errors: list[dict] = []
        self._memory_worker_events: list[dict] = []
        self._memory_analytics_events: list[dict] = []
        self._rules = rules or self._load_rules_from_repository() or DEFAULT_SIMULATION_RULES
        self._rules_hash = rules_hash(self._rules)
        self._rules_revision = self._active_rules_revision()
        if not self._repository:
            self._ensure_memory_rules_baseline()
        self._engine = SimulationEngine(seed=seed, rules=self._rules)
        self._state = self._load_or_seed(boot_ticks=boot_ticks)
        self._ensure_catalyst_role_baseline()

    def health(self) -> dict:
        with self._lock:
            self._refresh()
            return self._health_locked()

    def simulation_health(self) -> dict:
        with self._lock:
            self._refresh()
            event_counts: dict[str, int] = {}
            for event in self._state.events:
                event_counts[event.event_type.value] = (
                    event_counts.get(event.event_type.value, 0) + 1
                )
            total_population = sum(
                population.population_count
                for population in self._state.populations.values()
            )
            collapsed_regions = sum(
                1 for region in self._state.regions.values() if region.collapsed
            )
            latest_snapshot = self._repository.latest_snapshot() if self._repository else None
            latest_heartbeat = (
                self._repository.latest_worker_heartbeat()
                if self._repository
                else None
            )
            return {
                **self._health_locked(),
                "eventCounts": event_counts,
                "population": total_population,
                "collapsedRegions": collapsed_regions,
                "activeCatalystActions": len(self._state.catalyst_actions),
                "snapshots": self._repository.snapshot_count() if self._repository else 0,
                "latestSnapshot": _public_snapshot(latest_snapshot),
                "worker": _public_heartbeat(latest_heartbeat),
                "workerStaleSeconds": _heartbeat_age_seconds(latest_heartbeat),
            }

    def simulation_controls(self) -> dict:
        with self._lock:
            self._refresh()
            return self._simulation_controls_payload()

    def simulation_runs(self, *, limit: int = 50, offset: int = 0) -> dict:
        with self._lock:
            self._refresh()
            limit = max(1, min(limit, 100))
            offset = max(0, offset)
            if self._repository:
                page = self._repository.admin_simulation_runs(
                    limit=limit,
                    offset=offset,
                )
                items = page["items"]
                total = page["total"]
            else:
                ordered = sorted(
                    self._memory_admin_runs,
                    key=lambda row: str(row["created_at"]),
                    reverse=True,
                )
                items = ordered[offset : offset + limit]
                total = len(ordered)
            return {
                "model": "admin_simulation_runs_v1",
                "runs": [_public_admin_run(row) for row in items],
                "pagination": _pagination(total=total, limit=limit, offset=offset),
            }

    def record_api_request(
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
        with self._lock:
            if self._repository:
                return self._repository.record_api_request_log(
                    method=method,
                    path=path,
                    route=route,
                    status_code=status_code,
                    duration_ms=duration_ms,
                    request_id=request_id,
                    user_id=user_id,
                    client_host=client_host,
                )
            row = {
                "id": f"req-memory-{uuid4().hex}",
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
            self._memory_api_requests.append(row)
            return row

    def record_api_error(
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
        with self._lock:
            if self._repository:
                return self._repository.record_api_error_log(
                    method=method,
                    path=path,
                    route=route,
                    status_code=status_code,
                    error_code=error_code,
                    message=message,
                    request_id=request_id,
                    payload=payload,
                )
            row = {
                "id": f"err-memory-{uuid4().hex}",
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
            self._memory_api_errors.append(row)
            return row

    def track_product_event(
        self,
        *,
        event_name: str,
        user_id: str | None = None,
        session_id: str | None = None,
        subject_type: str | None = None,
        subject_id: str | None = None,
        source: str = "api",
        metadata: dict | None = None,
    ) -> dict:
        with self._lock:
            event_name = _analytics_event_name(event_name)
            source = _analytics_source(source)
            universe_id = self._state.universe.id
            if self._repository:
                row = self._repository.record_product_analytics_event(
                    universe_id=universe_id,
                    event_name=event_name,
                    user_id=user_id,
                    session_id=session_id,
                    subject_type=subject_type,
                    subject_id=subject_id,
                    source=source,
                    metadata=metadata,
                )
            else:
                row = {
                    "id": f"analytics-memory-{uuid4().hex}",
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
                self._memory_analytics_events.append(row)
            return {
                "model": "product_analytics_event_v1",
                "event": _public_analytics_event(row),
            }

    def observability_summary(self) -> dict:
        with self._lock:
            self._refresh()
            request_summary = (
                self._repository.api_request_summary()
                if self._repository
                else _api_request_summary(self._memory_api_requests)
            )
            error_summary = (
                self._repository.api_error_summary()
                if self._repository
                else _api_error_summary(self._memory_api_errors)
            )
            worker_summary = (
                self._repository.worker_run_summary()
                if self._repository
                else _worker_run_summary(self._memory_worker_events)
            )
            analytics_summary = (
                self._repository.product_analytics_summary()
                if self._repository
                else _product_analytics_summary(self._memory_analytics_events)
            )
            return {
                "model": "observability_summary_v1",
                "universe": self._admin_state_summary(),
                "requests": request_summary,
                "errors": error_summary,
                "worker": {
                    **worker_summary,
                    "latestHeartbeat": _public_heartbeat(
                        self._repository.latest_worker_heartbeat()
                        if self._repository
                        else None
                    ),
                },
                "analytics": analytics_summary,
            }

    def observability_requests(self, *, limit: int = 50, offset: int = 0) -> dict:
        with self._lock:
            limit = max(1, min(limit, 100))
            offset = max(0, offset)
            if self._repository:
                page = self._repository.api_request_logs_page(limit=limit, offset=offset)
                items = page["items"]
                total = page["total"]
            else:
                ordered = _ordered_rows(self._memory_api_requests)
                items = ordered[offset : offset + limit]
                total = len(ordered)
            return {
                "model": "api_request_logs_v1",
                "requests": [_public_api_request(row) for row in items],
                "pagination": _pagination(total=total, limit=limit, offset=offset),
            }

    def observability_errors(self, *, limit: int = 50, offset: int = 0) -> dict:
        with self._lock:
            limit = max(1, min(limit, 100))
            offset = max(0, offset)
            if self._repository:
                page = self._repository.api_error_logs_page(limit=limit, offset=offset)
                items = page["items"]
                total = page["total"]
            else:
                ordered = _ordered_rows(self._memory_api_errors)
                items = ordered[offset : offset + limit]
                total = len(ordered)
            return {
                "model": "api_error_logs_v1",
                "errors": [_public_api_error(row) for row in items],
                "pagination": _pagination(total=total, limit=limit, offset=offset),
            }

    def observability_worker_events(self, *, limit: int = 50, offset: int = 0) -> dict:
        with self._lock:
            limit = max(1, min(limit, 100))
            offset = max(0, offset)
            if self._repository:
                page = self._repository.worker_run_events_page(limit=limit, offset=offset)
                items = page["items"]
                total = page["total"]
            else:
                ordered = _ordered_rows(self._memory_worker_events)
                items = ordered[offset : offset + limit]
                total = len(ordered)
            return {
                "model": "worker_run_events_v1",
                "events": [_public_worker_event(row) for row in items],
                "pagination": _pagination(total=total, limit=limit, offset=offset),
            }

    def analytics_events(self, *, limit: int = 50, offset: int = 0) -> dict:
        with self._lock:
            limit = max(1, min(limit, 100))
            offset = max(0, offset)
            if self._repository:
                page = self._repository.product_analytics_events_page(
                    limit=limit,
                    offset=offset,
                )
                items = page["items"]
                total = page["total"]
            else:
                ordered = _ordered_rows(self._memory_analytics_events)
                items = ordered[offset : offset + limit]
                total = len(ordered)
            return {
                "model": "product_analytics_events_v1",
                "events": [_public_analytics_event(row) for row in items],
                "pagination": _pagination(total=total, limit=limit, offset=offset),
            }

    def run_simulation_batch(
        self,
        *,
        ticks: int,
        actor_id: str = "local-admin",
        reason: str | None = None,
    ) -> dict:
        with self._lock:
            ticks = _admin_ticks(ticks)
            actor_id = _admin_actor_id(actor_id)
            before = self._admin_state_summary()
            health = self.advance(ticks=ticks)
            after = self._admin_state_summary()
            run = self._record_admin_simulation_run(
                action_type="batch_tick",
                status="completed",
                actor_id=actor_id,
                reason=reason,
                requested_ticks=ticks,
                applied_ticks=health["tick"] - before["tick"],
                seed=self._seed,
                before=before,
                after=after,
                payload={
                    "requestedTicks": ticks,
                    "result": "advanced",
                },
            )
            return {
                "model": "admin_simulation_batch_v1",
                "run": _public_admin_run(run),
                "before": before,
                "after": after,
                "health": health,
                "controls": self._simulation_controls_payload(),
            }

    def reset_simulation(
        self,
        *,
        actor_id: str = "local-admin",
        reason: str | None = None,
        seed: int | None = None,
        boot_ticks: int | None = None,
        preserve_user_state: bool = True,
        confirm_reset: bool = False,
    ) -> dict:
        with self._lock:
            if not confirm_reset:
                raise ValueError("confirmReset must be true")
            actor_id = _admin_actor_id(actor_id)
            boot_ticks = _admin_boot_ticks(self._boot_ticks if boot_ticks is None else boot_ticks)
            before = self._admin_state_summary()
            next_seed = self._seed if seed is None else int(seed)
            self._seed = next_seed
            self._boot_ticks = boot_ticks
            self._engine = SimulationEngine(seed=self._seed, rules=self._rules)
            state = seed_alpha(seed=self._seed)
            self._engine.advance(state, ticks=boot_ticks)
            if self._repository:
                self._repository.reset_alpha(
                    state,
                    preserve_user_state=preserve_user_state,
                )
            else:
                self._memory_catalyst_counts.clear()
                self._memory_catalyst_action_logs.clear()
                if not preserve_user_state:
                    self._memory_follows.clear()
                    self._memory_notification_reads.clear()
            self._state = state
            self._ensure_catalyst_role_baseline()
            after = self._admin_state_summary()
            run = self._record_admin_simulation_run(
                action_type="seed_reset",
                status="completed",
                actor_id=actor_id,
                reason=reason,
                requested_ticks=boot_ticks,
                applied_ticks=after["tick"],
                seed=self._seed,
                before=before,
                after=after,
                payload={
                    "seed": self._seed,
                    "bootTicks": boot_ticks,
                    "preserveUserState": preserve_user_state,
                },
            )
            return {
                "model": "admin_simulation_reset_v1",
                "run": _public_admin_run(run),
                "before": before,
                "after": after,
                "controls": self._simulation_controls_payload(),
            }

    def simulation_rules(self) -> dict:
        with self._lock:
            self._refresh_rules()
            active_config = self._active_rules_config()
            revision = (
                int(active_config["revision"])
                if active_config and active_config.get("revision") is not None
                else self._rules_revision
            )
        return {
            "model": "simulation_rules_v1",
            "mode": "editable",
            "source": "backend/app/simulation/rules.py",
            "revision": revision,
            "rulesHash": self._rules_hash,
            "rules": rules_to_public(self._rules),
            "governance": {
                "validation": "enabled",
                "auditLog": "enabled",
                "rollback": "enabled",
                "writeSurface": "api_and_admin_ui",
                "uiEditable": True,
                "reloadStrategy": reload_strategy(runtime_applied=False),
            },
        }

    def validate_simulation_rules(
        self,
        rules_update: dict,
        *,
        actor_id: str,
        reason: str | None = None,
    ) -> dict:
        with self._lock:
            self._refresh_rules()
            result = validate_rules_update(rules_update, self._rules)
            strategy = reload_strategy(runtime_applied=False)
            audit = self._record_rules_audit(
                action_type="validate",
                status="accepted" if result.valid else "rejected",
                actor_id=actor_id,
                reason=reason,
                current_rules_hash=self._rules_hash,
                candidate_rules_hash=result.rules_hash if result.valid else None,
                validation_errors=result.errors,
                reload_strategy=strategy,
                payload={"candidateRules": rules_update},
            )
            return _rules_validation_response(result, audit, strategy)

    def apply_simulation_rules(
        self,
        rules_update: dict,
        *,
        actor_id: str,
        reason: str | None = None,
    ) -> dict:
        with self._lock:
            self._refresh_rules(force=True)
            previous_hash = self._rules_hash
            result = validate_rules_update(rules_update, self._rules)
            if not result.valid:
                strategy = reload_strategy(runtime_applied=False)
                audit = self._record_rules_audit(
                    action_type="apply",
                    status="rejected",
                    actor_id=actor_id,
                    reason=reason,
                    current_rules_hash=self._rules_hash,
                    candidate_rules_hash=None,
                    validation_errors=result.errors,
                    reload_strategy=strategy,
                    payload={"candidateRules": rules_update},
                )
                raise RuleConfigValidationError(
                    _rules_validation_response(result, audit, strategy)
                )

            self._ensure_rules_baseline(actor_id=actor_id)
            config = self._save_rules_config(
                rules=result.public_rules,
                rules_hash=result.rules_hash,
                actor_id=actor_id,
                reason=reason,
            )
            self._set_rules(result.rules, revision=int(config["revision"]))
            strategy = reload_strategy(runtime_applied=True)
            audit = self._record_rules_audit(
                action_type="apply",
                status="accepted",
                actor_id=actor_id,
                reason=reason,
                current_rules_hash=previous_hash,
                candidate_rules_hash=result.rules_hash,
                target_revision=int(config["revision"]),
                reload_strategy=strategy,
                payload={"configId": config["id"]},
            )
            return {
                "applied": True,
                "revision": int(config["revision"]),
                "rulesHash": result.rules_hash,
                "rules": result.public_rules,
                "audit": _public_rule_audit(audit),
                "reloadStrategy": strategy,
            }

    def rollback_simulation_rules(
        self,
        *,
        actor_id: str,
        reason: str | None = None,
        target_revision: int | None = None,
    ) -> dict:
        with self._lock:
            self._refresh_rules(force=True)
            previous_hash = self._rules_hash
            target = self._rules_config_by_revision(target_revision) if target_revision else self._previous_rules_config()
            if target is None:
                strategy = reload_strategy(runtime_applied=False)
                audit = self._record_rules_audit(
                    action_type="rollback",
                    status="rejected",
                    actor_id=actor_id,
                    reason=reason,
                    current_rules_hash=self._rules_hash,
                    target_revision=target_revision,
                    validation_errors=[
                        {
                            "path": "targetRevision",
                            "message": "No previous rules config is available.",
                        }
                    ],
                    reload_strategy=strategy,
                )
                raise RuleConfigRollbackError(
                    f"No rollback target is available. auditId={audit['id']}"
                )
            restored_rules = rules_from_public(target["rules"])
            restored_hash = rules_hash(restored_rules)
            config = self._save_rules_config(
                rules=target["rules"],
                rules_hash=restored_hash,
                actor_id=actor_id,
                reason=reason or f"Rollback to revision {target['revision']}",
            )
            self._set_rules(restored_rules, revision=int(config["revision"]))
            strategy = reload_strategy(runtime_applied=True)
            audit = self._record_rules_audit(
                action_type="rollback",
                status="accepted",
                actor_id=actor_id,
                reason=reason,
                current_rules_hash=previous_hash,
                candidate_rules_hash=restored_hash,
                target_revision=int(target["revision"]),
                reload_strategy=strategy,
                payload={
                    "restoredFromRevision": int(target["revision"]),
                    "newRevision": int(config["revision"]),
                    "configId": config["id"],
                },
            )
            return {
                "rolledBack": True,
                "restoredFromRevision": int(target["revision"]),
                "revision": int(config["revision"]),
                "rulesHash": restored_hash,
                "rules": target["rules"],
                "audit": _public_rule_audit(audit),
                "reloadStrategy": strategy,
            }

    def simulation_rules_audit(self, *, limit: int = 50, offset: int = 0) -> dict:
        with self._lock:
            if self._repository:
                page = self._repository.simulation_rules_audit(
                    limit=limit,
                    offset=offset,
                )
                items = page["items"]
                total = page["total"]
            else:
                ordered = list(reversed(self._memory_rule_audit))
                items = ordered[offset : offset + limit]
                total = len(ordered)
            return {
                "audit": [_public_rule_audit(item) for item in items],
                "pagination": _pagination(total=total, limit=limit, offset=offset),
            }

    def simulation_rules_revisions(self, *, limit: int = 20, offset: int = 0) -> dict:
        with self._lock:
            if self._repository:
                page = self._repository.simulation_rules_revisions(
                    limit=limit,
                    offset=offset,
                )
                items = page["items"]
                total = page["total"]
            else:
                ordered = sorted(
                    self._memory_rule_configs,
                    key=lambda item: int(item["revision"]),
                    reverse=True,
                )
                items = ordered[offset : offset + limit]
                total = len(ordered)
            return {
                "revisions": [_public_rule_config(item) for item in items],
                "pagination": _pagination(total=total, limit=limit, offset=offset),
            }

    def observer_follows(self, *, user_id: str = "local-observer") -> dict:
        with self._lock:
            self._refresh()
            user_id = _observer_user_id(user_id)
            follows = self._follow_rows(user_id)
            return _observer_follows_response(user_id, self._state, follows)

    def follow_entity(
        self,
        *,
        user_id: str,
        entity_type: str,
        entity_id: str,
    ) -> dict | None:
        with self._lock:
            self._refresh()
            user_id = _observer_user_id(user_id)
            entity_type = _observer_entity_type(entity_type)
            if not _entity_exists(self._state, entity_type, entity_id):
                return None
            if self._repository:
                follow = self._repository.save_observer_follow(
                    user_id=user_id,
                    entity_type=entity_type,
                    entity_id=entity_id,
                )
            else:
                follow = self._save_memory_follow(
                    user_id=user_id,
                    entity_type=entity_type,
                    entity_id=entity_id,
                )
            self.track_product_event(
                event_name="follow",
                user_id=user_id,
                subject_type=entity_type,
                subject_id=entity_id,
                source="server",
            )
            follows = self._follow_rows(user_id)
            return {
                "followed": True,
                "follow": _public_follow(follow, self._state),
                **_observer_follows_response(user_id, self._state, follows),
            }

    def unfollow_entity(
        self,
        *,
        user_id: str,
        entity_type: str,
        entity_id: str,
    ) -> dict | None:
        with self._lock:
            self._refresh()
            user_id = _observer_user_id(user_id)
            entity_type = _observer_entity_type(entity_type)
            if not _entity_exists(self._state, entity_type, entity_id):
                return None
            if self._repository:
                removed = self._repository.delete_observer_follow(
                    user_id=user_id,
                    entity_type=entity_type,
                    entity_id=entity_id,
                )
            else:
                removed = self._delete_memory_follow(
                    user_id=user_id,
                    entity_type=entity_type,
                    entity_id=entity_id,
                )
            follows = self._follow_rows(user_id)
            return {
                "followed": False,
                "removed": removed,
                **_observer_follows_response(user_id, self._state, follows),
            }

    def notifications(
        self,
        *,
        user_id: str = "local-observer",
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        with self._lock:
            self._refresh()
            user_id = _observer_user_id(user_id)
            limit = max(1, min(limit, 100))
            offset = max(0, offset)
            follows = self._follow_rows(user_id)
            reads = self._notification_reads(user_id)
            notifications = _project_notifications(
                user_id,
                self._state,
                follows=follows,
                reads=reads,
            )
            unread_count = sum(1 for item in notifications if not item["read"])
            filtered = [
                item for item in notifications if not unread_only or not item["read"]
            ]
            page = filtered[offset : offset + limit]
            return {
                "model": "observer_notifications_v1",
                "user": _observer_user(user_id),
                "notifications": page,
                "unreadCount": unread_count,
                "filters": {"unreadOnly": unread_only},
                "pagination": _pagination(
                    total=len(filtered),
                    limit=limit,
                    offset=offset,
                ),
            }

    def mark_notification_read(
        self,
        *,
        user_id: str,
        notification_id: str,
    ) -> dict | None:
        with self._lock:
            self._refresh()
            user_id = _observer_user_id(user_id)
            follows = self._follow_rows(user_id)
            reads = self._notification_reads(user_id)
            notifications = _project_notifications(
                user_id,
                self._state,
                follows=follows,
                reads=reads,
            )
            notification = next(
                (item for item in notifications if item["id"] == notification_id),
                None,
            )
            if notification is None:
                return None
            read = self._record_notification_read(
                user_id=user_id,
                notification_id=notification_id,
            )
            notification["read"] = True
            notification["readAt"] = _created_at(read)
            return {
                "markedRead": True,
                "notification": notification,
            }

    def mark_all_notifications_read(self, *, user_id: str) -> dict:
        with self._lock:
            self._refresh()
            user_id = _observer_user_id(user_id)
            follows = self._follow_rows(user_id)
            reads = self._notification_reads(user_id)
            notifications = _project_notifications(
                user_id,
                self._state,
                follows=follows,
                reads=reads,
            )
            marked = 0
            for notification in notifications:
                if notification["read"]:
                    continue
                self._record_notification_read(
                    user_id=user_id,
                    notification_id=notification["id"],
                )
                marked += 1
            return {
                "markedRead": True,
                "markedCount": marked,
                "unreadCount": 0,
                "user": _observer_user(user_id),
            }

    def catalyst_status(
        self,
        *,
        user_id: str = "local-catalyst",
        region_id: str | None = None,
    ) -> dict:
        with self._lock:
            self._refresh()
            user_id = _catalyst_user_id(user_id)
            if region_id is not None and region_id not in self._state.regions:
                raise ValueError(f"Unknown region id: {region_id}")
            return self._catalyst_capability_payload(user_id, region_id=region_id)

    def catalyst_actions(
        self,
        *,
        user_id: str = "local-catalyst",
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        with self._lock:
            self._refresh()
            user_id = _catalyst_user_id(user_id)
            limit = max(1, min(limit, 100))
            offset = max(0, offset)
            if self._repository:
                page = self._repository.catalyst_action_logs_for_user(
                    user_id=user_id,
                    limit=limit,
                    offset=offset,
                )
                items = page["items"]
                total = page["total"]
            else:
                logs = [
                    row
                    for row in self._memory_catalyst_action_logs.values()
                    if row["user_id"] == user_id
                ]
                ordered = sorted(
                    logs,
                    key=lambda row: (int(row["created_at_tick"]), row["id"]),
                    reverse=True,
                )
                items = ordered[offset : offset + limit]
                total = len(ordered)
            return {
                "model": "catalyst_actions_v1",
                "user": _catalyst_user(user_id, self._catalyst_role(user_id)),
                "actions": [
                    _public_catalyst_action_result(row, self._state)
                    for row in items
                ],
                "pagination": _pagination(total=total, limit=limit, offset=offset),
            }

    def catalyst_action_detail(
        self,
        *,
        action_id: str,
        user_id: str = "local-catalyst",
    ) -> dict | None:
        with self._lock:
            self._refresh()
            user_id = _catalyst_user_id(user_id)
            if self._repository:
                row = self._repository.catalyst_action_log(
                    action_id=action_id,
                    user_id=user_id,
                )
            else:
                row = self._memory_catalyst_action_logs.get(action_id)
                if row and row["user_id"] != user_id:
                    row = None
            if row is None:
                return None
            return {
                "model": "catalyst_action_result_v1",
                "user": _catalyst_user(user_id, self._catalyst_role(user_id)),
                "action": _public_catalyst_action_result(row, self._state),
            }

    def grant_catalyst_role(
        self,
        *,
        user_id: str,
        role: str = "catalyst",
        status: str = "active",
        granted_by: str = "local-admin",
    ) -> dict:
        with self._lock:
            self._refresh()
            user_id = _catalyst_user_id(user_id)
            role = _catalyst_role_value(role)
            status = _catalyst_role_status(status)
            granted_by = _catalyst_user_id(granted_by)
            row = self._save_catalyst_role(
                user_id=user_id,
                role=role,
                status=status,
                granted_by=granted_by,
            )
            return {
                "model": "catalyst_user_role_v1",
                "user": _catalyst_user(user_id, row),
                "role": _public_catalyst_role(row),
                "capabilities": self._catalyst_capability_payload(user_id),
            }

    def identity_context(
        self,
        *,
        observer_user_id: str = LOCAL_OBSERVER_USER_ID,
        catalyst_user_id: str = LOCAL_CATALYST_USER_ID,
        admin_actor_id: str = LOCAL_ADMIN_ACTOR_ID,
        region_id: str | None = None,
    ) -> dict:
        with self._lock:
            self._refresh()
            observer_user_id = _observer_user_id(observer_user_id)
            catalyst_user_id = _catalyst_user_id(catalyst_user_id)
            admin_actor_id = _admin_actor_id(admin_actor_id)
            if region_id is not None and region_id not in self._state.regions:
                raise ValueError(f"Unknown region id: {region_id}")

            catalyst_capabilities = self._catalyst_capability_payload(
                catalyst_user_id,
                region_id=region_id,
            )
            admin_role = self._catalyst_role(admin_actor_id)

            return {
                "model": "identity_context_v1",
                "mode": "local_alpha",
                "auth": {
                    "provider": self._auth_provider,
                    "status": "configured" if self._auth_provider == "google" else "deferred",
                    "nextProvider": "google",
                    "source": "session_headers_or_explicit_ids",
                    "sessionStrategy": "trusted_header" if self._auth_trusted_header_required else "local_bridge",
                    "localFallback": self._auth_allow_local_fallback,
                    "trustedHeaderRequired": self._auth_trusted_header_required,
                    "googleClientConfigured": bool(self._auth_google_client_id),
                },
                "users": {
                    "observer": _observer_user(observer_user_id),
                    "catalyst": catalyst_capabilities["user"],
                    "admin": _admin_user(admin_actor_id, admin_role),
                },
                "capabilities": {
                    "observer": {
                        "canFollow": True,
                        "canReceiveNotifications": True,
                    },
                    "catalyst": {
                        "permission": catalyst_capabilities["permission"],
                        "quotas": catalyst_capabilities["quotas"],
                        "cooldowns": catalyst_capabilities["cooldowns"],
                        "regionId": catalyst_capabilities["regionId"],
                    },
                    "admin": {
                        "canUseAdmin": _admin_can_act(admin_role),
                        "reason": None if _admin_can_act(admin_role) else "admin_role_required",
                    },
                },
                "roleGate": {
                    "observerAccess": "open_local",
                    "catalystAccess": "invite_or_role_gate",
                    "adminAccess": "active_admin_role",
                    "subscription": "deferred",
                },
            }

    def ensure_admin_permission(
        self,
        *,
        actor_id: str = LOCAL_ADMIN_ACTOR_ID,
    ) -> dict:
        with self._lock:
            self._refresh()
            actor_id = _admin_actor_id(actor_id)
            role = self._catalyst_role(actor_id)
            if not _admin_can_act(role):
                raise AdminPermissionError(f"Admin role is required for {actor_id}")
            return _admin_user(actor_id, role)

    def universe(self) -> dict:
        with self._lock:
            self._refresh()
            return serialize_universe(self._state)

    def latest_snapshot(self) -> dict:
        with self._lock:
            self._refresh()
            snapshot = self._repository.latest_snapshot() if self._repository else None
            if snapshot is None:
                snapshot = _snapshot_from_state(self._state)
            return {
                "universe": serialize_universe(self._state),
                "snapshot": _public_snapshot(snapshot),
            }

    def snapshot_details(self, tick: int) -> dict | None:
        with self._lock:
            self._refresh()
            if self._repository:
                details = self._repository.snapshot_details(tick)
            elif self._state.universe.tick == tick:
                details = _snapshot_details_from_state(self._state)
            else:
                details = None
            if details is None:
                return None
            regions = details["regions"]
            species = details["species"]
            populations = details["populations"]
            return {
                "universe": serialize_universe(self._state),
                "snapshot": _public_snapshot(details["snapshot"]),
                "coverage": {
                    "regionSnapshots": len(regions),
                    "speciesSnapshots": len(species),
                    "populationSnapshots": len(populations),
                },
                "regions": [_public_region_snapshot(row) for row in regions],
                "species": [_public_species_snapshot(row) for row in species],
                "populations": [
                    _public_population_snapshot(row)
                    for row in populations
                ],
            }

    def snapshots(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        from_age: int | None = None,
        to_age: int | None = None,
    ) -> dict:
        with self._lock:
            self._refresh()
            if self._repository:
                page = self._repository.snapshots(
                    limit=limit,
                    offset=offset,
                    from_world_age=from_age,
                    to_world_age=to_age,
                )
                items = page["items"]
                total = page["total"]
            else:
                page = _paginate_snapshot_list(
                    [_snapshot_from_state(self._state)],
                    limit=limit,
                    offset=offset,
                    from_age=from_age,
                    to_age=to_age,
                )
                items = page["items"]
                total = page["total"]
            return {
                "universe": serialize_universe(self._state),
                "snapshots": [_public_snapshot(snapshot) for snapshot in items],
                "filters": {
                    "fromAge": from_age,
                    "toAge": to_age,
                },
                "pagination": _pagination(
                    total=total,
                    limit=limit,
                    offset=offset,
                ),
            }

    def dynamic_report(
        self,
        *,
        scope: str = "universe",
        limit: int = 12,
        from_age: int | None = None,
        to_age: int | None = None,
        region_id: str | None = None,
        species_id: str | None = None,
    ) -> dict | None:
        with self._lock:
            self._refresh()
            page = self._report_snapshot_page(
                limit=limit,
                from_age=from_age,
                to_age=to_age,
            )
            snapshots = sorted(page["items"], key=lambda item: int(item["tick"]))
            if not snapshots:
                return None
            series, detail_count = self._report_series(
                snapshots,
                scope=scope,
                region_id=region_id,
                species_id=species_id,
            )
            if not series:
                return None
            baseline = series[0]
            current = series[-1]
            return {
                "model": "dynamic_report_v1",
                "scope": {
                    "type": scope,
                    "regionId": region_id,
                    "speciesId": species_id,
                },
                "universe": serialize_universe(self._state),
                "filters": {
                    "limit": limit,
                    "fromAge": from_age,
                    "toAge": to_age,
                },
                "baseline": baseline,
                "current": current,
                "delta": _metric_delta(baseline["metrics"], current["metrics"]),
                "series": series,
                "coverage": {
                    "snapshotCount": len(snapshots),
                    "seriesCount": len(series),
                    "detailSnapshotCount": detail_count,
                    "totalSnapshots": page["total"],
                },
            }

    def landing(self) -> dict:
        with self._lock:
            self._refresh()
            self.track_product_event(
                event_name="landing_view",
                subject_type="universe",
                subject_id=self._state.universe.id,
                source="server",
            )
            featured_events = sorted(
                self._state.events,
                key=lambda event: (event.severity, event.world_age, event.id),
                reverse=True,
            )[:5]
            chronicle_preview = list(reversed(self._state.events[-10:]))
            return {
                "universe": serialize_universe(self._state),
                "featuredEvents": [
                    serialize_event(event, self._state) for event in featured_events
                ],
                "chroniclePreview": [
                    serialize_event(event, self._state) for event in chronicle_preview
                ],
                "regions": self._map_regions(limit=108),
                "species": [
                    serialize_species(species, self._state)
                    for species in sorted(
                        self._state.species.values(),
                        key=lambda item: item.name,
                    )[:8]
                ],
            }

    def _report_snapshot_page(
        self,
        *,
        limit: int,
        from_age: int | None,
        to_age: int | None,
    ) -> dict:
        if self._repository:
            return self._repository.snapshots(
                limit=limit,
                offset=0,
                from_world_age=from_age,
                to_world_age=to_age,
            )
        return _paginate_snapshot_list(
            [_snapshot_from_state(self._state)],
            limit=limit,
            offset=0,
            from_age=from_age,
            to_age=to_age,
        )

    def _report_series(
        self,
        snapshots: list[dict],
        *,
        scope: str,
        region_id: str | None,
        species_id: str | None,
    ) -> tuple[list[dict], int]:
        if scope == "universe":
            series = [
                _universe_report_point(snapshot, self._snapshot_details(int(snapshot["tick"])))
                for snapshot in snapshots
            ]
            detail_count = sum(1 for point in series if point["metadata"]["detailCoverage"])
            return series, detail_count

        series: list[dict] = []
        detail_count = 0
        for snapshot in snapshots:
            details = self._snapshot_details(int(snapshot["tick"]))
            if details is None:
                continue
            detail_count += 1
            point = _entity_report_point(
                details,
                scope=scope,
                region_id=region_id,
                species_id=species_id,
            )
            if point is not None:
                series.append(point)
        return series, detail_count

    def _snapshot_details(self, tick: int) -> dict | None:
        if self._repository:
            return self._repository.snapshot_details(tick)
        if self._state.universe.tick == tick:
            return _snapshot_details_from_state(self._state)
        return None

    def chronicle(self, time_filter: str = "all", limit: int = 50, offset: int = 0) -> dict:
        with self._lock:
            self._refresh()
            events = self._filter_events(time_filter)
            page = _paginate_events(events, limit=limit, offset=offset)
            return {
                "universe": serialize_universe(self._state),
                "timeFilter": time_filter,
                "events": [
                    serialize_event(event, self._state) for event in page["items"]
                ],
                "pagination": page["pagination"],
            }

    def event_stream(
        self,
        *,
        last_event_id: str | None = None,
        limit: int = 25,
    ) -> dict:
        with self._lock:
            self._refresh()
            limit = max(1, min(limit, 100))
            events = self._state.events
            latest_cursor = events[-1].id if events else None
            if last_event_id is None:
                return {
                    "model": "event_stream_v1",
                    "universe": serialize_universe(self._state),
                    "cursor": latest_cursor,
                    "lastEventId": None,
                    "missedCursor": False,
                    "hasMore": False,
                    "limit": limit,
                    "events": [],
                }

            cursor_index = _event_index(events, last_event_id)
            if cursor_index is None:
                selected = events[-limit:]
                missed_cursor = True
                has_more = False
            else:
                start = cursor_index + 1
                selected = events[start : start + limit]
                missed_cursor = False
                has_more = start + len(selected) < len(events)

            cursor = selected[-1].id if selected else last_event_id
            return {
                "model": "event_stream_v1",
                "universe": serialize_universe(self._state),
                "cursor": cursor,
                "lastEventId": last_event_id,
                "missedCursor": missed_cursor,
                "hasMore": has_more,
                "limit": limit,
                "events": [
                    serialize_event(event, self._state) for event in selected
                ],
            }

    def regions(self, mode: str = "life") -> dict:
        with self._lock:
            self._refresh()
            return {
                "universe": serialize_universe(self._state),
                "mode": mode,
                "regions": self._map_regions(limit=None),
            }

    def region_detail(self, region_id: str) -> dict | None:
        with self._lock:
            self._refresh()
            detail = self._region_detail_locked(region_id)
            if detail is not None:
                self.track_product_event(
                    event_name="detail_view",
                    subject_type="region",
                    subject_id=region_id,
                    source="server",
                )
            return detail

    def _region_detail_locked(self, region_id: str) -> dict | None:
        region = self._state.regions.get(region_id)
        if region is None:
            return None
        populations = sorted(
            [
                population
                for population in self._state.populations.values()
                if population.region_id == region.id and population.population_count > 0
            ],
            key=lambda item: item.population_count,
            reverse=True,
        )
        events = [
            event for event in self._state.events if event.region_id == region.id
        ]
        return {
            "region": serialize_region(region, self._state),
            "populations": [
                serialize_population(population, self._state)
                for population in populations[:10]
            ],
            "events": [
                serialize_event(event, self._state)
                for event in reversed(events[-25:])
            ],
        }

    def region_events(self, region_id: str, limit: int = 50, offset: int = 0) -> dict | None:
        with self._lock:
            self._refresh()
            if region_id not in self._state.regions:
                return None
            events = [
                event for event in self._state.events if event.region_id == region_id
            ]
            page = _paginate_events(events, limit=limit, offset=offset)
            return {
                "regionId": region_id,
                "events": [
                    serialize_event(event, self._state)
                    for event in page["items"]
                ],
                "pagination": page["pagination"],
            }

    def species_list(self) -> dict:
        with self._lock:
            self._refresh()
            species = sorted(
                self._state.species.values(),
                key=lambda item: serialize_species(item, self._state)["population"],
                reverse=True,
            )
            return {
                "universe": serialize_universe(self._state),
                "species": [
                    serialize_species(item, self._state) for item in species
                ],
            }

    def species_detail(self, species_id: str) -> dict | None:
        with self._lock:
            self._refresh()
            species = self._state.species.get(species_id)
            if species is None:
                return None
            self.track_product_event(
                event_name="detail_view",
                subject_type="species",
                subject_id=species_id,
                source="server",
            )
            events = [
                event for event in self._state.events if event.species_id == species_id
            ]
            children = [
                item for item in self._state.species.values() if item.parent_species_id == species_id
            ]
            return {
                "species": serialize_species(species, self._state),
                "children": [
                    serialize_species(item, self._state) for item in children
                ],
                "events": [
                    serialize_event(event, self._state)
                    for event in reversed(events[-25:])
                ],
            }

    def species_forecast(self, species_id: str) -> dict | None:
        with self._lock:
            self._refresh()
            species = self._state.species.get(species_id)
            if species is None:
                return None
            serialized_species = serialize_species(species, self._state)
            return {
                "universe": serialize_universe(self._state),
                "species": {
                    "id": serialized_species["id"],
                    "name": serialized_species["name"],
                    "status": serialized_species["status"],
                    "population": serialized_species["population"],
                    "originRegionId": serialized_species["originRegionId"],
                    "generation": serialized_species["generation"],
                },
                "forecast": serialize_species_forecast(species, self._state),
                "model": "forecast_lite_v1",
                "generatedAtWorldAge": self._state.universe.age_years,
            }

    def species_events(self, species_id: str, limit: int = 50, offset: int = 0) -> dict | None:
        with self._lock:
            self._refresh()
            if species_id not in self._state.species:
                return None
            events = [
                event for event in self._state.events if event.species_id == species_id
            ]
            page = _paginate_events(events, limit=limit, offset=offset)
            return {
                "speciesId": species_id,
                "events": [
                    serialize_event(event, self._state)
                    for event in page["items"]
                ],
                "pagination": page["pagination"],
            }

    def catalyst_action(
        self,
        region_id: str,
        action_type: str,
        *,
        user_id: str = "local-catalyst",
    ) -> dict:
        with self._lock:
            user_id = _catalyst_user_id(user_id)
            for attempt in range(3):
                self._refresh(force=True)
                action_type_enum = CatalystActionType(action_type)
                day_key = _current_day_key()
                self._ensure_catalyst_permission(user_id)
                self._ensure_catalyst_allowed(
                    region_id=region_id,
                    action_type=action_type_enum,
                    user_id=user_id,
                    day_key=day_key,
                )
                base_tick = self._state.universe.tick
                action = self._engine.register_catalyst_action(
                    self._state,
                    region_id=region_id,
                    action_type=action_type_enum,
                    user_id=user_id,
                )
                self._annotate_catalyst_event(action.id, day_key=day_key)
                self._engine.advance(
                    self._state,
                    ticks=self._rules.catalyst.followup_ticks,
                )
                action_log = _catalyst_action_log(
                    action,
                    day_key=day_key,
                    world_age=self._state.universe.age_years,
                )
                try:
                    self._save(
                        expected_tick=base_tick,
                        catalyst_action_log=action_log,
                    )
                except AlphaStateConflictError:
                    if attempt == 2:
                        raise
                    continue
                self._record_memory_catalyst_action(action_log=action_log)
                self.track_product_event(
                    event_name="catalyst_action",
                    user_id=user_id,
                    subject_type="region",
                    subject_id=region_id,
                    source="server",
                    metadata={"actionType": action.action_type.value},
                )
                return {
                    "model": "catalyst_action_result_v1",
                    "accepted": True,
                    "status": "accepted",
                    "message": "Influence initiated",
                    "user": _catalyst_user(user_id, self._catalyst_role(user_id)),
                    "action": {
                        "id": action.id,
                        "regionId": action.region_id,
                        "actionType": action.action_type.value,
                        "createdAtTick": action.created_at_tick,
                        "expiresAtTick": action.expires_at_tick,
                        "expiresAtWorldAge": self._state.universe.age_years
                        + max(0, action.expires_at_tick - self._state.universe.tick),
                    },
                    "tracking": _public_catalyst_action_result(action_log, self._state),
                    "capabilities": self._catalyst_capability_payload(
                        user_id,
                        region_id=region_id,
                    ),
                    "region": self._region_detail_locked(region_id),
                }
            raise RuntimeError("Catalyst action could not be persisted")

    def advance(self, ticks: int = 1) -> dict:
        with self._lock:
            for attempt in range(3):
                self._refresh(force=True)
                base_tick = self._state.universe.tick
                self._engine.advance(self._state, ticks=ticks)
                try:
                    self._save(expected_tick=base_tick)
                except AlphaStateConflictError:
                    if attempt == 2:
                        raise
                    continue
                return self._health_locked()
            raise RuntimeError("Alpha advance could not be persisted")

    def _follow_rows(self, user_id: str) -> list[dict]:
        if self._repository:
            return self._repository.observer_follows(user_id=user_id)
        return [
            row
            for row in self._memory_follows.values()
            if row["universe_id"] == "alpha" and row["user_id"] == user_id
        ]

    def _save_memory_follow(
        self,
        *,
        user_id: str,
        entity_type: str,
        entity_id: str,
    ) -> dict:
        key = ("alpha", user_id, entity_type, entity_id)
        existing = self._memory_follows.get(key)
        if existing is not None:
            return existing
        row = {
            "id": f"follow-memory-{uuid4().hex}",
            "universe_id": "alpha",
            "user_id": user_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "created_at": datetime.now(UTC),
        }
        self._memory_follows[key] = row
        return row

    def _delete_memory_follow(
        self,
        *,
        user_id: str,
        entity_type: str,
        entity_id: str,
    ) -> bool:
        key = ("alpha", user_id, entity_type, entity_id)
        return self._memory_follows.pop(key, None) is not None

    def _notification_reads(self, user_id: str) -> dict[str, dict]:
        if self._repository:
            return self._repository.notification_reads(user_id=user_id)
        return {
            notification_id: row
            for (stored_user_id, notification_id), row in self._memory_notification_reads.items()
            if stored_user_id == user_id
        }

    def _record_notification_read(
        self,
        *,
        user_id: str,
        notification_id: str,
    ) -> dict:
        if self._repository:
            return self._repository.record_notification_read(
                user_id=user_id,
                notification_id=notification_id,
            )
        row = {
            "universe_id": "alpha",
            "user_id": user_id,
            "notification_id": notification_id,
            "read_at": datetime.now(UTC),
        }
        self._memory_notification_reads[(user_id, notification_id)] = row
        return row

    def _load_rules_from_repository(self) -> SimulationRules | None:
        if not self._repository:
            return None
        config = self._repository.latest_simulation_rules_config()
        if config is None:
            return None
        return rules_from_public(config["rules"])

    def _active_rules_revision(self) -> int:
        config = self._active_rules_config()
        return int(config["revision"]) if config else 1

    def _active_rules_config(self) -> dict | None:
        if self._repository:
            return self._repository.latest_simulation_rules_config()
        return next(
            (
                config
                for config in self._memory_rule_configs
                if bool(config.get("is_active"))
            ),
            None,
        )

    def _rules_config_by_revision(self, revision: int | None) -> dict | None:
        if revision is None:
            return None
        if self._repository:
            return self._repository.simulation_rules_config_by_revision(revision)
        return next(
            (
                config
                for config in self._memory_rule_configs
                if int(config["revision"]) == revision
            ),
            None,
        )

    def _previous_rules_config(self) -> dict | None:
        if self._repository:
            return self._repository.previous_simulation_rules_config()
        active = self._active_rules_config()
        if active is None:
            return None
        previous = [
            config
            for config in self._memory_rule_configs
            if int(config["revision"]) < int(active["revision"])
        ]
        return max(previous, key=lambda item: int(item["revision"])) if previous else None

    def _ensure_rules_baseline(self, *, actor_id: str) -> None:
        if self._repository:
            if self._repository.latest_simulation_rules_config() is None:
                self._repository.save_simulation_rules_config(
                    universe_id="alpha",
                    rules=rules_to_public(self._rules),
                    rules_hash=self._rules_hash,
                    actor_id=actor_id,
                    reason="Baseline before first editable rules change.",
                )
            return
        self._ensure_memory_rules_baseline()

    def _ensure_memory_rules_baseline(self) -> None:
        if self._memory_rule_configs:
            return
        self._memory_rule_configs.append(
            {
                "id": "rules-memory-baseline",
                "universe_id": "alpha",
                "revision": 1,
                "rules_hash": self._rules_hash,
                "rules": rules_to_public(self._rules),
                "applied_by": "system",
                "reason": "Initial in-memory rules baseline.",
                "is_active": True,
                "created_at": datetime.now(UTC),
            }
        )
        self._rules_revision = 1

    def _save_rules_config(
        self,
        *,
        rules: dict,
        rules_hash: str,
        actor_id: str,
        reason: str | None,
    ) -> dict:
        if self._repository:
            return self._repository.save_simulation_rules_config(
                universe_id="alpha",
                rules=rules,
                rules_hash=rules_hash,
                actor_id=actor_id,
                reason=reason,
            )
        for config in self._memory_rule_configs:
            config["is_active"] = False
        revision = max(
            (int(config["revision"]) for config in self._memory_rule_configs),
            default=0,
        ) + 1
        config = {
            "id": f"rules-memory-{uuid4().hex}",
            "universe_id": "alpha",
            "revision": revision,
            "rules_hash": rules_hash,
            "rules": rules,
            "applied_by": actor_id,
            "reason": reason,
            "is_active": True,
            "created_at": datetime.now(UTC),
        }
        self._memory_rule_configs.append(config)
        return config

    def _record_rules_audit(
        self,
        *,
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
        if self._repository:
            return self._repository.record_simulation_rules_audit(
                universe_id="alpha",
                action_type=action_type,
                status=status,
                actor_id=actor_id,
                reason=reason,
                current_rules_hash=current_rules_hash,
                candidate_rules_hash=candidate_rules_hash,
                target_revision=target_revision,
                validation_errors=validation_errors,
                reload_strategy=reload_strategy,
                payload=payload,
            )
        audit = {
            "id": f"rules-audit-memory-{uuid4().hex}",
            "universe_id": "alpha",
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
            "created_at": datetime.now(UTC),
        }
        self._memory_rule_audit.append(audit)
        return audit

    def _refresh_rules(self, *, force: bool = False) -> None:
        if not self._repository or (not force and not self._refresh_on_read):
            return
        config = self._repository.latest_simulation_rules_config()
        if config is None or config["rules_hash"] == self._rules_hash:
            return
        self._set_rules(
            rules_from_public(config["rules"]),
            revision=int(config["revision"]),
        )

    def _set_rules(self, rules: SimulationRules, *, revision: int) -> None:
        self._rules = rules
        self._rules_hash = rules_hash(rules)
        self._rules_revision = revision
        self._engine = SimulationEngine(seed=self._seed, rules=self._rules)

    def _map_regions(self, limit: int | None) -> list[dict]:
        regions = sorted(self._state.regions.values(), key=lambda item: (item.y, item.x))
        if limit is not None:
            regions = regions[:limit]
        return [serialize_region(region, self._state) for region in regions]

    def _filter_events(self, time_filter: str) -> list:
        if time_filter == "now":
            minimum_age = self._state.universe.age_years - 12
        elif time_filter == "last_24h":
            minimum_age = self._state.universe.age_years - 24
        elif time_filter == "last_7d":
            minimum_age = self._state.universe.age_years - 168
        else:
            return self._state.events
        return [
            event for event in self._state.events if event.world_age >= minimum_age
        ]

    def event_type_coverage(self) -> set[EventType]:
        with self._lock:
            self._refresh()
            return {event.event_type for event in self._state.events}

    def _load_or_seed(self, *, boot_ticks: int):
        if self._repository:
            loaded = self._repository.load_alpha(seed=self._seed)
            if loaded:
                return loaded
        state = seed_alpha(seed=self._seed)
        self._engine.advance(state, ticks=boot_ticks)
        if self._repository:
            self._repository.save_alpha(state)
        return state

    def _refresh(self, *, force: bool = False) -> None:
        self._refresh_rules(force=force)
        if not self._repository or (not force and not self._refresh_on_read):
            return
        loaded = self._repository.load_alpha(seed=self._seed)
        if loaded:
            self._state = loaded

    def _save(
        self,
        *,
        expected_tick: int | None = None,
        catalyst_action_log: dict | None = None,
    ) -> None:
        if self._repository:
            self._repository.save_alpha(
                self._state,
                expected_tick=expected_tick,
                catalyst_action_log=catalyst_action_log,
            )

    def _persistence_name(self) -> str:
        return self._repository.persistence_name if self._repository else "memory"

    def _health_locked(self) -> dict:
        return {
            "status": "ok",
            "persistence": self._persistence_name(),
            "universe": self._state.universe.id,
            "ageYears": self._state.universe.age_years,
            "tick": self._state.universe.tick,
            "regions": len(self._state.regions),
            "species": len(self._state.species),
            "events": len(self._state.events),
        }

    def _admin_state_summary(self) -> dict:
        total_population = sum(
            population.population_count
            for population in self._state.populations.values()
        )
        collapsed_regions = sum(
            1 for region in self._state.regions.values() if region.collapsed
        )
        return {
            "universe": self._state.universe.id,
            "ageYears": self._state.universe.age_years,
            "tick": self._state.universe.tick,
            "era": self._state.universe.current_era.value,
            "stabilityIndex": round(self._state.universe.stability_index, 3),
            "regions": len(self._state.regions),
            "species": len(self._state.species),
            "population": total_population,
            "events": len(self._state.events),
            "collapsedRegions": collapsed_regions,
            "activeCatalystActions": len(self._state.catalyst_actions),
        }

    def _simulation_controls_payload(self) -> dict:
        latest_heartbeat = (
            self._repository.latest_worker_heartbeat()
            if self._repository
            else None
        )
        active_config = self._active_rules_config()
        rules_revision = (
            int(active_config["revision"])
            if active_config and active_config.get("revision") is not None
            else self._rules_revision
        )
        return {
            "model": "admin_simulation_controls_v1",
            "universe": self._admin_state_summary(),
            "mode": {
                "runtime": "api_manual_batch",
                "worker": _worker_control_state(latest_heartbeat),
                "publicTickExposure": "hidden",
            },
            "controls": {
                "batchTick": {
                    "enabled": True,
                    "minTicks": 1,
                    "maxTicks": 500,
                    "endpoint": "POST /admin/simulation/batches",
                },
                "seedReset": {
                    "enabled": True,
                    "requiresConfirmReset": True,
                    "defaultBootTicks": self._boot_ticks,
                    "endpoint": "POST /admin/simulation/reset",
                },
                "editableRules": {
                    "uiEditable": False,
                    "validation": "enabled",
                    "auditLog": "enabled",
                    "rollback": "enabled",
                },
            },
            "worker": {
                "separateProcess": True,
                "heartbeat": _public_heartbeat(latest_heartbeat),
            },
            "rules": {
                "revision": rules_revision,
                "rulesHash": self._rules_hash,
                "reloadStrategy": reload_strategy(runtime_applied=False),
            },
            "debug": {
                "visibility": "admin_only",
                "persistence": self._persistence_name(),
                "seed": self._seed,
                "bootTicks": self._boot_ticks,
                "apiRefreshOnRead": self._refresh_on_read,
                "eventCount": len(self._state.events),
                "snapshotCount": self._repository.snapshot_count() if self._repository else 1,
            },
        }

    def _record_admin_simulation_run(
        self,
        *,
        action_type: str,
        status: str,
        actor_id: str,
        reason: str | None,
        requested_ticks: int,
        applied_ticks: int,
        seed: int,
        before: dict,
        after: dict,
        payload: dict | None = None,
    ) -> dict:
        if self._repository:
            return self._repository.record_admin_simulation_run(
                universe_id=self._state.universe.id,
                action_type=action_type,
                status=status,
                actor_id=actor_id,
                reason=reason,
                requested_ticks=requested_ticks,
                applied_ticks=applied_ticks,
                seed=seed,
                before_tick=before["tick"],
                after_tick=after["tick"],
                before_world_age=before["ageYears"],
                after_world_age=after["ageYears"],
                payload=payload,
            )
        row = {
            "id": f"admin-run-memory-{uuid4().hex}",
            "universe_id": self._state.universe.id,
            "action_type": action_type,
            "status": status,
            "actor_id": actor_id,
            "reason": reason,
            "requested_ticks": requested_ticks,
            "applied_ticks": applied_ticks,
            "seed": seed,
            "before_tick": before["tick"],
            "after_tick": after["tick"],
            "before_world_age": before["ageYears"],
            "after_world_age": after["ageYears"],
            "payload": payload or {},
            "created_at": datetime.now(UTC),
        }
        self._memory_admin_runs.append(row)
        return row

    def _ensure_catalyst_allowed(
        self,
        *,
        region_id: str,
        action_type: CatalystActionType,
        user_id: str,
        day_key: str,
    ) -> None:
        if region_id not in self._state.regions:
            raise ValueError(f"Unknown region id: {region_id}")
        cooldown_action = next(
            (
                action
                for action in self._state.catalyst_actions
                if action.region_id == region_id
                and action.expires_at_tick > self._state.universe.tick
            ),
            None,
        )
        if cooldown_action:
            retry_after = max(1, cooldown_action.expires_at_tick - self._state.universe.tick)
            raise CatalystCooldownError(
                f"{region_id} is cooling down for {retry_after} more ticks"
            )
        limit = self._rules.catalyst.daily_limits[action_type]
        used = self._catalyst_count(
            user_id=user_id,
            action_type=action_type,
            day_key=day_key,
        )
        if used >= limit:
            raise CatalystLimitError(
                f"Daily {action_type.value} limit reached for {user_id}: {used}/{limit}"
            )

    def _ensure_catalyst_permission(self, user_id: str) -> None:
        role = self._catalyst_role(user_id)
        if not _catalyst_can_act(role):
            raise CatalystPermissionError(
                f"Catalyst role is required for {user_id}"
            )

    def _catalyst_count(
        self,
        *,
        user_id: str,
        action_type: CatalystActionType,
        day_key: str,
    ) -> int:
        if self._repository:
            return self._repository.catalyst_action_count(
                user_id=user_id,
                action_type=action_type.value,
                day_key=day_key,
            )
        return self._memory_catalyst_counts.get(
            (user_id, action_type.value, day_key),
            0,
        )

    def _record_memory_catalyst_action(
        self,
        *,
        action_log: dict,
    ) -> None:
        key = (
            action_log["user_id"],
            action_log["action_type"],
            action_log["day_key"],
        )
        self._memory_catalyst_counts[key] = self._memory_catalyst_counts.get(key, 0) + 1
        if self._repository:
            return
        self._memory_catalyst_action_logs[action_log["id"]] = {
            **action_log,
            "created_at": None,
        }

    def _catalyst_role(self, user_id: str) -> dict | None:
        if self._repository:
            return self._repository.catalyst_user_role(user_id=user_id)
        return self._memory_catalyst_roles.get((self._state.universe.id, user_id))

    def _save_catalyst_role(
        self,
        *,
        user_id: str,
        role: str,
        status: str,
        granted_by: str,
    ) -> dict:
        if self._repository:
            return self._repository.save_catalyst_user_role(
                user_id=user_id,
                role=role,
                status=status,
                granted_by=granted_by,
            )
        now = datetime.now(UTC)
        key = (self._state.universe.id, user_id)
        existing = self._memory_catalyst_roles.get(key)
        row = {
            "universe_id": self._state.universe.id,
            "user_id": user_id,
            "role": role,
            "status": status,
            "granted_by": granted_by,
            "created_at": existing["created_at"] if existing else now,
            "updated_at": now,
        }
        self._memory_catalyst_roles[key] = row
        return row

    def _ensure_catalyst_role_baseline(self) -> None:
        baseline_roles = {user_id: "catalyst" for user_id in self._bootstrap_catalysts}
        baseline_roles.update({user_id: "admin" for user_id in self._bootstrap_admins})
        for user_id, role in baseline_roles.items():
            if self._catalyst_role(user_id) is None:
                self._save_catalyst_role(
                    user_id=user_id,
                    role=role,
                    status="active",
                    granted_by="system",
                )
        # Repair env-declared admins. A pre-existing role row (e.g. a lower or
        # inactive grant from before the id was added to
        # EVOVERSE_AUTH_BOOTSTRAP_ADMINS) must not silently block admin access.
        # Only ever upgrade — never downgrade an existing admin.
        for user_id in self._bootstrap_admins:
            existing = self._catalyst_role(user_id)
            if existing is not None and (
                existing.get("role") != "admin" or existing.get("status") != "active"
            ):
                self._save_catalyst_role(
                    user_id=user_id,
                    role="admin",
                    status="active",
                    granted_by="system",
                )

    def _catalyst_capability_payload(
        self,
        user_id: str,
        *,
        region_id: str | None = None,
    ) -> dict:
        role = self._catalyst_role(user_id)
        can_act = _catalyst_can_act(role)
        day_key = _current_day_key()
        quotas = [
            self._catalyst_quota(action_type, user_id=user_id, day_key=day_key)
            for action_type in CatalystActionType
        ]
        active_actions = [
            action
            for action in self._state.catalyst_actions
            if region_id is None or action.region_id == region_id
        ]
        return {
            "model": "catalyst_capabilities_v1",
            "user": _catalyst_user(user_id, role),
            "permission": {
                "canUseCatalyst": can_act,
                "reason": None if can_act else "catalyst_role_required",
            },
            "quotas": quotas,
            "cooldowns": [
                _public_catalyst_cooldown(action, self._state)
                for action in sorted(
                    active_actions,
                    key=lambda item: (item.expires_at_tick, item.id),
                )
            ],
            "regionId": region_id,
        }

    def _catalyst_quota(
        self,
        action_type: CatalystActionType,
        *,
        user_id: str,
        day_key: str,
    ) -> dict:
        limit = self._rules.catalyst.daily_limits[action_type]
        used = self._catalyst_count(
            user_id=user_id,
            action_type=action_type,
            day_key=day_key,
        )
        return {
            "actionType": action_type.value,
            "dayKey": day_key,
            "limit": limit,
            "used": used,
            "remaining": max(0, limit - used),
        }

    def _annotate_catalyst_event(self, action_id: str, *, day_key: str) -> None:
        for event in reversed(self._state.events):
            if event.payload.get("action_id") == action_id:
                event.payload["day_key"] = day_key
                return


def _paginate_events(events, *, limit: int, offset: int) -> dict:
    ordered = list(reversed(events))
    total = len(ordered)
    offset = max(0, offset)
    limit = max(1, limit)
    items = ordered[offset : offset + limit]
    return {
        "items": items,
        "pagination": {
            "limit": limit,
            "offset": offset,
            "total": total,
            "hasMore": offset + limit < total,
            "nextOffset": offset + limit if offset + limit < total else None,
        },
    }


def _event_index(events, event_id: str) -> int | None:
    for index, event in enumerate(events):
        if event.id == event_id:
            return index
    return None


def _observer_user_id(user_id: str | None) -> str:
    normalized = (user_id or LOCAL_OBSERVER_USER_ID).strip()
    if not normalized:
        raise ValueError("userId is required")
    return normalized


def _admin_actor_id(actor_id: str | None) -> str:
    normalized = (actor_id or LOCAL_ADMIN_ACTOR_ID).strip()
    if not normalized:
        raise ValueError("actorId is required")
    return normalized


def _bootstrap_ids(values: tuple[str, ...] | None, *, fallback: str | None) -> tuple[str, ...]:
    normalized = tuple(dict.fromkeys(item.strip() for item in (values or ()) if item.strip()))
    if normalized:
        return normalized
    return (fallback,) if fallback else ()


def _admin_ticks(ticks: int) -> int:
    value = int(ticks)
    if value < 1 or value > 500:
        raise ValueError("ticks must be between 1 and 500")
    return value


def _admin_boot_ticks(boot_ticks: int) -> int:
    value = int(boot_ticks)
    if value < 0 or value > 10000:
        raise ValueError("bootTicks must be between 0 and 10000")
    return value


def _observer_entity_type(entity_type: str) -> str:
    if entity_type not in {"region", "species"}:
        raise ValueError(f"Unsupported follow entity type: {entity_type}")
    return entity_type


def _entity_exists(state, entity_type: str, entity_id: str) -> bool:
    if entity_type == "region":
        return entity_id in state.regions
    if entity_type == "species":
        return entity_id in state.species
    return False


def _observer_user(user_id: str) -> dict:
    return {
        "id": user_id,
        "mode": "local_observer",
        "auth": "deferred",
    }


def _catalyst_user_id(user_id: str | None) -> str:
    normalized = (user_id or LOCAL_CATALYST_USER_ID).strip()
    if not normalized:
        raise ValueError("userId is required")
    return normalized


def _catalyst_role_value(role: str | None) -> str:
    normalized = (role or "catalyst").strip().lower()
    if normalized not in CATALYST_ROLES:
        raise ValueError(f"Unsupported Catalyst role: {role}")
    return normalized


def _catalyst_role_status(status: str | None) -> str:
    normalized = (status or "active").strip().lower()
    if normalized not in CATALYST_ROLE_STATUSES:
        raise ValueError(f"Unsupported Catalyst role status: {status}")
    return normalized


def _catalyst_can_act(role: dict | None) -> bool:
    return (
        role is not None
        and role.get("role") in CATALYST_ROLES
        and role.get("status") == "active"
    )


def _catalyst_user(user_id: str, role: dict | None) -> dict:
    role_name = role["role"] if role else "observer"
    status = role["status"] if role else "guest"
    return {
        "id": user_id,
        "mode": "local_catalyst",
        "auth": "deferred",
        "role": role_name,
        "status": status,
    }


def _admin_can_act(role: dict | None) -> bool:
    return (
        role is not None
        and role.get("role") == "admin"
        and role.get("status") == "active"
    )


def _admin_user(actor_id: str, role: dict | None) -> dict:
    role_name = role["role"] if role else "observer"
    status = role["status"] if role else "guest"
    return {
        "id": actor_id,
        "mode": "local_admin",
        "auth": "deferred",
        "role": role_name,
        "status": status,
    }


def _public_catalyst_role(role: dict) -> dict:
    return {
        "universeId": role["universe_id"],
        "userId": role["user_id"],
        "role": role["role"],
        "status": role["status"],
        "grantedBy": role["granted_by"],
        "createdAt": _created_at(role),
        "updatedAt": str(role["updated_at"]) if role.get("updated_at") is not None else None,
    }


def _observer_follows_response(user_id: str, state, follows: list[dict]) -> dict:
    public_follows = [
        follow for follow in (_public_follow(row, state) for row in follows) if follow
    ]
    regions = [follow for follow in public_follows if follow["entityType"] == "region"]
    species = [follow for follow in public_follows if follow["entityType"] == "species"]
    return {
        "model": "observer_follows_v1",
        "user": _observer_user(user_id),
        "follows": {
            "regions": regions,
            "species": species,
        },
        "counts": {
            "regions": len(regions),
            "species": len(species),
            "total": len(regions) + len(species),
        },
    }


def _public_follow(row: dict, state) -> dict | None:
    entity_type = row["entity_type"]
    entity_id = row["entity_id"]
    if entity_type == "region":
        region = state.regions.get(entity_id)
        if region is None:
            return None
        entity = serialize_region(region, state)
    elif entity_type == "species":
        species = state.species.get(entity_id)
        if species is None:
            return None
        entity = serialize_species(species, state)
    else:
        return None
    return {
        "id": row["id"],
        "universeId": row["universe_id"],
        "userId": row["user_id"],
        "entityType": entity_type,
        "entityId": entity_id,
        "entity": entity,
        "createdAt": _created_at(row),
    }


def _project_notifications(
    user_id: str,
    state,
    *,
    follows: list[dict],
    reads: dict[str, dict],
) -> list[dict]:
    followed_regions = {
        row["entity_id"]
        for row in follows
        if row["entity_type"] == "region" and row["entity_id"] in state.regions
    }
    followed_species = {
        row["entity_id"]
        for row in follows
        if row["entity_type"] == "species" and row["entity_id"] in state.species
    }
    notifications: list[dict] = []
    for event in state.events:
        if event.region_id in followed_regions:
            notifications.append(
                _notification(
                    user_id,
                    state,
                    event,
                    reads,
                    kind="followed_region_event",
                    target_type="region",
                    target_id=event.region_id,
                )
            )
        if event.species_id in followed_species:
            notifications.append(
                _notification(
                    user_id,
                    state,
                    event,
                    reads,
                    kind="followed_species_event",
                    target_type="species",
                    target_id=event.species_id,
                )
            )
        if (
            event.event_type == EventType.CATALYST_ACTION
            and event.payload.get("user_id") == user_id
        ):
            notifications.append(
                _notification(
                    user_id,
                    state,
                    event,
                    reads,
                    kind="catalyst_action",
                    target_type="region",
                    target_id=event.region_id,
                )
            )
        if user_id in _payload_list(event.payload.get("catalyst_user_ids")):
            notifications.append(
                _notification(
                    user_id,
                    state,
                    event,
                    reads,
                    kind="catalyst_downstream_event",
                    target_type="species" if event.species_id else "region",
                    target_id=event.species_id or event.region_id,
                )
            )
    notifications.sort(
        key=lambda item: (
            item["event"]["worldAge"],
            item["event"]["id"],
            item["id"],
        ),
        reverse=True,
    )
    return notifications


def _notification(
    user_id: str,
    state,
    event,
    reads: dict[str, dict],
    *,
    kind: str,
    target_type: str,
    target_id: str | None,
) -> dict:
    target_key = target_id or "alpha"
    notification_id = f"notif-{event.id}-{kind}-{target_key}"
    read = reads.get(notification_id)
    return {
        "id": notification_id,
        "model": "observer_notification_v1",
        "userId": user_id,
        "kind": kind,
        "title": event.title,
        "summary": event.summary,
        "read": read is not None,
        "readAt": _created_at(read) if read else None,
        "target": _notification_target(state, target_type, target_id),
        "event": serialize_event(event, state),
        "createdAt": event.created_at,
    }


def _notification_target(state, target_type: str, target_id: str | None) -> dict | None:
    if target_id is None:
        return None
    if target_type == "region":
        region = state.regions.get(target_id)
        if region is None:
            return None
        return {
            "type": "region",
            "id": region.id,
            "label": region.id,
        }
    if target_type == "species":
        species = state.species.get(target_id)
        if species is None:
            return None
        return {
            "type": "species",
            "id": species.id,
            "label": species.name,
        }
    return None


def _public_admin_run(row: dict) -> dict:
    return {
        "id": row["id"],
        "universeId": row["universe_id"],
        "actionType": row["action_type"],
        "status": row["status"],
        "actorId": row["actor_id"],
        "reason": row["reason"],
        "requestedTicks": int(row["requested_ticks"]),
        "appliedTicks": int(row["applied_ticks"]),
        "seed": int(row["seed"]),
        "before": {
            "tick": int(row["before_tick"]),
            "worldAge": int(row["before_world_age"]),
        },
        "after": {
            "tick": int(row["after_tick"]),
            "worldAge": int(row["after_world_age"]),
        },
        "payload": row["payload"] or {},
        "createdAt": _created_at(row),
    }


def _public_api_request(row: dict) -> dict:
    return {
        "id": row["id"],
        "method": row["method"],
        "path": row["path"],
        "route": row["route"],
        "statusCode": int(row["status_code"]),
        "durationMs": _float(row["duration_ms"]),
        "requestId": row["request_id"],
        "userId": row["user_id"],
        "clientHost": row["client_host"],
        "createdAt": _created_at(row),
    }


def _public_api_error(row: dict) -> dict:
    return {
        "id": row["id"],
        "method": row["method"],
        "path": row["path"],
        "route": row["route"],
        "statusCode": int(row["status_code"]),
        "errorCode": row["error_code"],
        "message": row["message"],
        "requestId": row["request_id"],
        "payload": row["payload"] or {},
        "createdAt": _created_at(row),
    }


def _public_worker_event(row: dict) -> dict:
    return {
        "id": row["id"],
        "workerId": row["worker_id"],
        "universeId": row["universe_id"],
        "eventType": row["event_type"],
        "status": row["status"],
        "lastTick": int(row["last_tick"]),
        "lastWorldAge": int(row["last_world_age"]),
        "lastStep": int(row["last_step"]),
        "error": row["error"],
        "payload": row["payload"] or {},
        "createdAt": _created_at(row),
    }


def _public_analytics_event(row: dict) -> dict:
    return {
        "id": row["id"],
        "universeId": row["universe_id"],
        "eventName": row["event_name"],
        "userId": row["user_id"],
        "sessionId": row["session_id"],
        "subjectType": row["subject_type"],
        "subjectId": row["subject_id"],
        "source": row["source"],
        "metadata": row["metadata"] or {},
        "createdAt": _created_at(row),
    }


def _api_request_summary(rows: list[dict]) -> dict:
    total = len(rows)
    errors_4xx = sum(1 for row in rows if 400 <= int(row["status_code"]) < 500)
    errors_5xx = sum(1 for row in rows if int(row["status_code"]) >= 500)
    total_duration = sum(float(row["duration_ms"]) for row in rows)
    status_codes: dict[str, int] = {}
    for row in rows:
        key = str(int(row["status_code"]))
        status_codes[key] = status_codes.get(key, 0) + 1
    return {
        "total": total,
        "errors4xx": errors_4xx,
        "errors5xx": errors_5xx,
        "averageDurationMs": round(total_duration / total, 3) if total else 0.0,
        "statusCodes": status_codes,
    }


def _api_error_summary(rows: list[dict]) -> dict:
    error_codes: dict[str, int] = {}
    for row in rows:
        key = str(row["error_code"])
        error_codes[key] = error_codes.get(key, 0) + 1
    return {
        "total": len(rows),
        "errorCodes": error_codes,
    }


def _worker_run_summary(rows: list[dict]) -> dict:
    counts: dict[str, int] = {}
    for row in rows:
        key = str(row["event_type"])
        counts[key] = counts.get(key, 0) + 1
    starts = counts.get("start", 0)
    return {
        "starts": starts,
        "completions": counts.get("complete", 0),
        "crashes": counts.get("error", 0),
        "restarts": max(0, starts - 1),
        "events": counts,
    }


def _product_analytics_summary(rows: list[dict]) -> dict:
    counts: dict[str, int] = {}
    for row in rows:
        key = str(row["event_name"])
        counts[key] = counts.get(key, 0) + 1
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


def _ordered_rows(rows: list[dict]) -> list[dict]:
    return sorted(rows, key=lambda row: str(row["created_at"]), reverse=True)


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 4)


def _analytics_event_name(event_name: str | None) -> str:
    normalized = (event_name or "").strip().lower()
    allowed = {
        "landing_view",
        "detail_view",
        "follow",
        "catalyst_action",
        "replay_interaction",
    }
    if normalized not in allowed:
        raise ValueError(f"Unsupported analytics event: {event_name}")
    return normalized


def _analytics_source(source: str | None) -> str:
    normalized = (source or "api").strip().lower()
    if not normalized:
        raise ValueError("source is required")
    return normalized


def _worker_control_state(heartbeat: dict | None) -> dict:
    if heartbeat is None:
        return {
            "status": "not_connected",
            "canUseManualBatch": True,
            "note": "No worker heartbeat has been recorded.",
        }
    if heartbeat["status"] == "error":
        return {
            "status": "error",
            "canUseManualBatch": True,
            "note": heartbeat["last_error"],
        }
    return {
        "status": "connected",
        "canUseManualBatch": True,
        "note": "Manual batch remains available for admin-controlled low activity windows.",
    }


def _public_catalyst_action_result(row: dict, state) -> dict:
    action_id = row["id"]
    source_event = _catalyst_source_event(action_id, state)
    downstream_events = _catalyst_downstream_events(action_id, state)
    active_action = next(
        (action for action in state.catalyst_actions if action.id == action_id),
        None,
    )
    if downstream_events:
        status = "influence_detected"
    elif active_action is not None:
        status = "influence_active"
    else:
        status = "influence_initiated"
    return {
        "id": action_id,
        "universeId": row["universe_id"],
        "userId": row["user_id"],
        "regionId": row["region_id"],
        "actionType": row["action_type"],
        "dayKey": row["day_key"],
        "createdAtTick": int(row["created_at_tick"]),
        "worldAge": int(row["world_age"]),
        "createdAt": _created_at(row),
        "status": status,
        "active": active_action is not None,
        "expiresAtTick": active_action.expires_at_tick if active_action else None,
        "region": _notification_target(state, "region", row["region_id"]),
        "sourceEvent": serialize_event(source_event, state) if source_event else None,
        "downstreamEventCount": len(downstream_events),
        "downstreamEvents": [
            serialize_event(event, state)
            for event in sorted(
                downstream_events,
                key=lambda item: (item.tick, item.id),
                reverse=True,
            )[:10]
        ],
    }


def _public_catalyst_cooldown(action, state) -> dict:
    retry_after_ticks = max(0, action.expires_at_tick - state.universe.tick)
    return {
        "actionId": action.id,
        "regionId": action.region_id,
        "actionType": action.action_type.value,
        "createdAtTick": action.created_at_tick,
        "expiresAtTick": action.expires_at_tick,
        "retryAfterTicks": retry_after_ticks,
    }


def _catalyst_source_event(action_id: str, state):
    return next(
        (
            event
            for event in state.events
            if event.event_type == EventType.CATALYST_ACTION
            and event.payload.get("action_id") == action_id
        ),
        None,
    )


def _catalyst_downstream_events(action_id: str, state) -> list:
    return [
        event
        for event in state.events
        if event.event_type != EventType.CATALYST_ACTION
        and action_id in _payload_list(event.payload.get("catalyst_action_ids"))
    ]


def _payload_list(value) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if value is None:
        return []
    return [value]


def _created_at(row: dict | None) -> str | None:
    if row is None:
        return None
    created_at = row.get("created_at") or row.get("read_at")
    return str(created_at) if created_at is not None else None


def _paginate_snapshot_list(
    snapshots: list[dict],
    *,
    limit: int,
    offset: int,
    from_age: int | None,
    to_age: int | None,
) -> dict:
    filtered = [
        snapshot
        for snapshot in snapshots
        if (from_age is None or int(snapshot["world_age"]) >= from_age)
        and (to_age is None or int(snapshot["world_age"]) <= to_age)
    ]
    ordered = sorted(filtered, key=lambda snapshot: int(snapshot["tick"]), reverse=True)
    return {
        "items": ordered[offset : offset + limit],
        "total": len(ordered),
    }


def _pagination(*, total: int, limit: int, offset: int) -> dict:
    return {
        "limit": limit,
        "offset": offset,
        "total": total,
        "hasMore": offset + limit < total,
        "nextOffset": offset + limit if offset + limit < total else None,
    }


def _public_snapshot(snapshot: dict | None) -> dict | None:
    if snapshot is None:
        return None
    created_at = snapshot["created_at"]
    return {
        "universeId": snapshot["universe_id"],
        "tick": int(snapshot["tick"]),
        "worldAge": int(snapshot["world_age"]),
        "regionCount": int(snapshot["region_count"]),
        "speciesCount": int(snapshot["species_count"]),
        "populationCount": int(snapshot["population_count"]),
        "eventCount": int(snapshot["event_count"]),
        "payload": snapshot["payload"],
        "createdAt": str(created_at) if created_at is not None else None,
    }


def _snapshot_from_state(state) -> dict:
    population_count = sum(
        population.population_count for population in state.populations.values()
    )
    return {
        "universe_id": state.universe.id,
        "tick": state.universe.tick,
        "world_age": state.universe.age_years,
        "region_count": len(state.regions),
        "species_count": len(state.species),
        "population_count": population_count,
        "event_count": len(state.events),
        "payload": {
            "snapshot_model": "entity_snapshots_v1",
            "stability_index": state.universe.stability_index,
            "active_catalyst_actions": len(state.catalyst_actions),
            "region_snapshot_count": len(state.regions),
            "species_snapshot_count": len(state.species),
            "population_snapshot_count": len(state.populations),
            "source": "memory",
        },
        "created_at": None,
    }


def _snapshot_details_from_state(state) -> dict:
    region_population_totals, region_species_counts = _region_snapshot_totals(state)
    species_population_totals, species_region_counts = _species_snapshot_totals(state)
    return {
        "snapshot": _snapshot_from_state(state),
        "regions": [
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
                },
                "created_at": None,
            }
            for region in sorted(state.regions.values(), key=lambda item: (item.y, item.x))
        ],
        "species": [
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
                },
                "created_at": None,
            }
            for item in sorted(
                state.species.values(),
                key=lambda species: (
                    -species_population_totals.get(species.id, 0),
                    species.id,
                ),
            )
        ],
        "populations": [
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
                "created_at": None,
            }
            for population in sorted(
                state.populations.values(),
                key=lambda item: (-item.population_count, item.species_id, item.region_id),
            )
        ],
    }


def _public_region_snapshot(snapshot: dict) -> dict:
    created_at = snapshot["created_at"]
    return {
        "universeId": snapshot["universe_id"],
        "tick": int(snapshot["tick"]),
        "worldAge": int(snapshot["world_age"]),
        "regionId": snapshot["region_id"],
        "x": int(snapshot["x"]),
        "y": int(snapshot["y"]),
        "biomeType": snapshot["biome_type"],
        "energyLevel": _float(snapshot["energy_level"]),
        "resourceDensity": _float(snapshot["resource_density"]),
        "stability": _float(snapshot["stability"]),
        "dominantSpeciesId": snapshot["dominant_species_id"],
        "collapsed": bool(snapshot["collapsed"]),
        "populationCount": int(snapshot["population_count"]),
        "speciesCount": int(snapshot["species_count"]),
        "payload": snapshot["payload"],
        "createdAt": str(created_at) if created_at is not None else None,
    }


def _public_species_snapshot(snapshot: dict) -> dict:
    created_at = snapshot["created_at"]
    return {
        "universeId": snapshot["universe_id"],
        "tick": int(snapshot["tick"]),
        "worldAge": int(snapshot["world_age"]),
        "speciesId": snapshot["species_id"],
        "name": snapshot["name"],
        "status": snapshot["status"],
        "originRegionId": snapshot["origin_region_id"],
        "generation": int(snapshot["generation"]),
        "parentSpeciesId": snapshot["parent_species_id"],
        "populationCount": int(snapshot["population_count"]),
        "regionCount": int(snapshot["region_count"]),
        "traits": snapshot["traits"],
        "payload": snapshot["payload"],
        "createdAt": str(created_at) if created_at is not None else None,
    }


def _public_population_snapshot(snapshot: dict) -> dict:
    created_at = snapshot["created_at"]
    return {
        "universeId": snapshot["universe_id"],
        "tick": int(snapshot["tick"]),
        "worldAge": int(snapshot["world_age"]),
        "speciesId": snapshot["species_id"],
        "regionId": snapshot["region_id"],
        "populationCount": int(snapshot["population_count"]),
        "energyConsumption": _float(snapshot["energy_consumption"]),
        "growthRate": _float(snapshot["growth_rate"]),
        "migrationPressure": _float(snapshot["migration_pressure"]),
        "payload": snapshot["payload"],
        "createdAt": str(created_at) if created_at is not None else None,
    }


def _universe_report_point(snapshot: dict, details: dict | None) -> dict:
    collapsed_regions = None
    if details is not None:
        collapsed_regions = sum(1 for region in details["regions"] if region["collapsed"])
    payload = snapshot["payload"] or {}
    metrics = {
        "regionCount": int(snapshot["region_count"]),
        "speciesCount": int(snapshot["species_count"]),
        "populationCount": int(snapshot["population_count"]),
        "eventCount": int(snapshot["event_count"]),
        "stabilityIndex": _float(payload.get("stability_index", 0.0)),
        "activeCatalystActions": int(payload.get("active_catalyst_actions", 0)),
    }
    if collapsed_regions is not None:
        metrics["collapsedRegionCount"] = collapsed_regions
    return {
        "tick": int(snapshot["tick"]),
        "worldAge": int(snapshot["world_age"]),
        "metrics": metrics,
        "metadata": {
            "detailCoverage": details is not None,
            "snapshotModel": payload.get("snapshot_model"),
        },
    }


def _entity_report_point(
    details: dict,
    *,
    scope: str,
    region_id: str | None,
    species_id: str | None,
) -> dict | None:
    if scope == "region":
        row = _find_snapshot(details["regions"], "region_id", region_id)
        return _region_report_point(row) if row is not None else None
    if scope == "species":
        row = _find_snapshot(details["species"], "species_id", species_id)
        return _species_report_point(row) if row is not None else None
    if scope == "population":
        row = next(
            (
                item
                for item in details["populations"]
                if item["region_id"] == region_id and item["species_id"] == species_id
            ),
            None,
        )
        return _population_report_point(row) if row is not None else None
    return None


def _region_report_point(snapshot: dict) -> dict:
    return {
        "tick": int(snapshot["tick"]),
        "worldAge": int(snapshot["world_age"]),
        "metrics": {
            "energyLevel": _float(snapshot["energy_level"]),
            "resourceDensity": _float(snapshot["resource_density"]),
            "stability": _float(snapshot["stability"]),
            "populationCount": int(snapshot["population_count"]),
            "speciesCount": int(snapshot["species_count"]),
            "collapsed": 1 if snapshot["collapsed"] else 0,
        },
        "metadata": {
            "regionId": snapshot["region_id"],
            "biomeType": snapshot["biome_type"],
            "dominantSpeciesId": snapshot["dominant_species_id"],
        },
    }


def _species_report_point(snapshot: dict) -> dict:
    traits = snapshot["traits"] or {}
    trait_values = [float(value) for value in traits.values()] or [0.0]
    return {
        "tick": int(snapshot["tick"]),
        "worldAge": int(snapshot["world_age"]),
        "metrics": {
            "populationCount": int(snapshot["population_count"]),
            "regionCount": int(snapshot["region_count"]),
            "generation": int(snapshot["generation"]),
            "traitStrength": round(sum(trait_values) / len(trait_values), 3),
        },
        "metadata": {
            "speciesId": snapshot["species_id"],
            "name": snapshot["name"],
            "status": snapshot["status"],
            "originRegionId": snapshot["origin_region_id"],
            "parentSpeciesId": snapshot["parent_species_id"],
        },
    }


def _population_report_point(snapshot: dict) -> dict:
    return {
        "tick": int(snapshot["tick"]),
        "worldAge": int(snapshot["world_age"]),
        "metrics": {
            "populationCount": int(snapshot["population_count"]),
            "energyConsumption": _float(snapshot["energy_consumption"]),
            "growthRate": _float(snapshot["growth_rate"]),
            "migrationPressure": _float(snapshot["migration_pressure"]),
        },
        "metadata": {
            "regionId": snapshot["region_id"],
            "speciesId": snapshot["species_id"],
        },
    }


def _find_snapshot(items: list[dict], key: str, value: str | None) -> dict | None:
    return next((item for item in items if item[key] == value), None)


def _metric_delta(baseline: dict, current: dict) -> dict:
    keys = sorted(set(baseline) | set(current))
    delta = {}
    for key in keys:
        start = baseline.get(key)
        end = current.get(key)
        if not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
            continue
        absolute = round(end - start, 6)
        percent = None
        if start != 0:
            percent = round((absolute / start) * 100, 3)
        delta[key] = {
            "from": start,
            "to": end,
            "absolute": absolute,
            "percent": percent,
        }
    return delta


def _region_snapshot_totals(state) -> tuple[dict[str, int], dict[str, int]]:
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


def _species_snapshot_totals(state) -> tuple[dict[str, int], dict[str, int]]:
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


def _float(value) -> float:
    return float(value)


def _public_heartbeat(heartbeat: dict | None) -> dict | None:
    if heartbeat is None:
        return None
    return {
        "workerId": heartbeat["worker_id"],
        "universeId": heartbeat["universe_id"],
        "status": heartbeat["status"],
        "lastTick": int(heartbeat["last_tick"]),
        "lastWorldAge": int(heartbeat["last_world_age"]),
        "lastStep": int(heartbeat["last_step"]),
        "lastError": heartbeat["last_error"],
        "updatedAt": str(heartbeat["updated_at"]),
    }


def _heartbeat_age_seconds(heartbeat: dict | None) -> float | None:
    if heartbeat is None:
        return None
    updated = heartbeat.get("updated_at")
    if not isinstance(updated, datetime):
        return None
    if updated.tzinfo is None:
        updated = updated.replace(tzinfo=UTC)
    return round((datetime.now(UTC) - updated).total_seconds(), 1)


def _rules_validation_response(result, audit: dict, strategy: dict) -> dict:
    return {
        "valid": result.valid,
        "rulesHash": result.rules_hash,
        "rules": result.public_rules if result.valid else None,
        "errors": result.errors,
        "warnings": result.warnings,
        "audit": _public_rule_audit(audit),
        "reloadStrategy": strategy,
    }


def _public_rule_config(config: dict) -> dict:
    created_at = config.get("created_at")
    return {
        "id": config["id"],
        "universeId": config["universe_id"],
        "revision": int(config["revision"]),
        "rulesHash": config["rules_hash"],
        "rules": config["rules"],
        "appliedBy": config["applied_by"],
        "reason": config["reason"],
        "isActive": bool(config["is_active"]),
        "createdAt": str(created_at) if created_at is not None else None,
    }


def _public_rule_audit(audit: dict) -> dict:
    created_at = audit.get("created_at")
    return {
        "id": audit["id"],
        "universeId": audit["universe_id"],
        "actionType": audit["action_type"],
        "status": audit["status"],
        "actorId": audit["actor_id"],
        "reason": audit["reason"],
        "currentRulesHash": audit["current_rules_hash"],
        "candidateRulesHash": audit["candidate_rules_hash"],
        "targetRevision": audit["target_revision"],
        "validationErrors": audit["validation_errors"],
        "reloadStrategy": audit["reload_strategy"],
        "payload": audit["payload"],
        "createdAt": str(created_at) if created_at is not None else None,
    }


def _public_rules(value):
    if isinstance(value, dict):
        return {
            _public_rule_key(key): _public_rules(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_public_rules(item) for item in value]
    if isinstance(value, Enum):
        return value.value
    return value


def _public_rule_key(key) -> str:
    if isinstance(key, Enum):
        return str(key.value)
    key_text = str(key)
    if "_" not in key_text:
        return key_text
    head, *tail = key_text.split("_")
    return head + "".join(part.capitalize() for part in tail)


def _current_day_key() -> str:
    return datetime.now(UTC).date().isoformat()


def _catalyst_action_log(action, *, day_key: str, world_age: int) -> dict:
    return {
        "id": action.id,
        "universe_id": action.universe_id,
        "region_id": action.region_id,
        "action_type": action.action_type.value,
        "user_id": action.user_id,
        "day_key": day_key,
        "created_at_tick": action.created_at_tick,
        "world_age": world_age,
    }
