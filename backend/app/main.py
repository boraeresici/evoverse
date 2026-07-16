from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any
from uuid import uuid4

from app.api.errors import ERROR_CODES, http_exception_handler, validation_exception_handler
from app.config import get_settings
from app.persistence import AlphaStateConflictError, create_alpha_repository
from app.persistence.repository import SNAPSHOT_FRAME_BUDGET
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from app.services import AlphaStore
from app.services.alpha_store import (
    AdminPermissionError,
    CatalystCooldownError,
    CatalystLimitError,
    CatalystPermissionError,
    LOCAL_ADMIN_ACTOR_ID,
    LOCAL_CATALYST_USER_ID,
    LOCAL_OBSERVER_USER_ID,
    RuleConfigRollbackError,
    RuleConfigValidationError,
)

SESSION_USER_ID_HEADER = "x-evoverse-user-id"
OBSERVER_USER_ID_HEADER = "x-evoverse-observer-id"
CATALYST_USER_ID_HEADER = "x-evoverse-catalyst-id"
ADMIN_ACTOR_ID_HEADER = "x-evoverse-admin-id"
AUTH_SECRET_HEADER = "x-evoverse-auth-secret"


class CatalystActionRequest(BaseModel):
    region_id: str = Field(alias="regionId")
    action_type: str = Field(alias="actionType")
    user_id: str = Field(default=LOCAL_CATALYST_USER_ID, alias="userId")


class SimulationRulesChangeRequest(BaseModel):
    rules: dict[str, Any] = Field(default_factory=dict)
    actor_id: str = Field(default=LOCAL_ADMIN_ACTOR_ID, alias="actorId")
    reason: str | None = None


class AdminSimulationBatchRequest(BaseModel):
    ticks: int = Field(default=1, ge=1, le=500)
    actor_id: str = Field(default=LOCAL_ADMIN_ACTOR_ID, alias="actorId")
    reason: str | None = None


class AdminSimulationResetRequest(BaseModel):
    actor_id: str = Field(default=LOCAL_ADMIN_ACTOR_ID, alias="actorId")
    reason: str | None = None
    seed: int | None = None
    boot_ticks: int | None = Field(default=None, ge=0, le=10000, alias="bootTicks")
    preserve_user_state: bool = Field(default=True, alias="preserveUserState")
    confirm_reset: bool = Field(default=False, alias="confirmReset")


class SimulationRulesRollbackRequest(BaseModel):
    actor_id: str = Field(default=LOCAL_ADMIN_ACTOR_ID, alias="actorId")
    reason: str | None = None
    target_revision: int | None = Field(default=None, alias="targetRevision")


class ObserverIdentityRequest(BaseModel):
    user_id: str = Field(default=LOCAL_OBSERVER_USER_ID, alias="userId")


class CatalystRoleRequest(BaseModel):
    role: str = "catalyst"
    status: str = "active"
    granted_by: str = Field(default=LOCAL_ADMIN_ACTOR_ID, alias="grantedBy")


class AnalyticsEventRequest(BaseModel):
    event_name: str = Field(alias="eventName")
    user_id: str | None = Field(default=None, alias="userId")
    session_id: str | None = Field(default=None, alias="sessionId")
    subject_type: str | None = Field(default=None, alias="subjectType")
    subject_id: str | None = Field(default=None, alias="subjectId")
    source: str = "client"
    metadata: dict[str, Any] = Field(default_factory=dict)


settings = get_settings()
repository = (
    create_alpha_repository(settings.database_url)
    if settings.use_postgres and settings.database_url
    else None
)
store = AlphaStore(
    seed=settings.seed,
    boot_ticks=settings.boot_ticks,
    repository=repository,
    refresh_on_read=settings.api_refresh_on_read,
    auth_provider=settings.auth_provider,
    auth_allow_local_fallback=settings.auth_allow_local_fallback,
    auth_trusted_header_required=bool(settings.auth_trusted_header_secret),
    auth_google_client_id=settings.auth_google_client_id,
    bootstrap_admins=settings.auth_bootstrap_admins,
    bootstrap_catalysts=settings.auth_bootstrap_catalysts,
    allow_local_admin=settings.allow_local_admin,
)

app = FastAPI(
    title="Evoverse API",
    version="0.1.0",
    description="Product API for Evoverse Alpha.",
)

app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("evoverse.api")

EVENT_STREAM_BATCH_LIMIT = 25
EVENT_STREAM_POLL_SECONDS = 2


@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    started = time.perf_counter()
    request_id = request.headers.get("x-request-id") or f"req-{uuid4().hex}"
    request.state.request_id = request_id
    status_code = 500
    route = None
    recorded = False
    try:
        response = await call_next(request)
        status_code = response.status_code
        route = _route_path(request)
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception as exc:
        route = _route_path(request)
        await _record_api_observation(
            request=request,
            route=route,
            status_code=500,
            duration_ms=_duration_ms(started),
            request_id=request_id,
            error_code="unhandled_exception",
            message=str(exc),
        )
        recorded = True
        logger.exception(
            "api_error method=%s path=%s status=500 request_id=%s",
            request.method,
            request.url.path,
            request_id,
        )
        raise
    finally:
        if not recorded:
            await _record_api_observation(
                request=request,
                route=route or _route_path(request),
                status_code=status_code,
                duration_ms=_duration_ms(started),
                request_id=request_id,
            )


def _sse_event(event_name: str, data: dict, *, event_id: str | None = None) -> str:
    lines = []
    if event_id:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event_name}")
    lines.append(f"data: {json.dumps(data, separators=(',', ':'))}")
    return "\n".join(lines) + "\n\n"


def _duration_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 3)


def _route_path(request: Request) -> str | None:
    route = request.scope.get("route")
    return getattr(route, "path", None)


def _request_user_id(request: Request) -> str | None:
    return (
        request.query_params.get("userId")
        or request.headers.get("x-evoverse-user-id")
    )


def _resolve_observer_user_id(request: Request, explicit_user_id: str | None = None) -> str:
    return _identity_from_request(
        request,
        (OBSERVER_USER_ID_HEADER, SESSION_USER_ID_HEADER),
        explicit_user_id,
        fallback=LOCAL_OBSERVER_USER_ID,
    )


def _resolve_catalyst_user_id(request: Request, explicit_user_id: str | None = None) -> str:
    return _identity_from_request(
        request,
        (CATALYST_USER_ID_HEADER, SESSION_USER_ID_HEADER),
        explicit_user_id,
        fallback=LOCAL_CATALYST_USER_ID,
    )


def _resolve_admin_actor_id(request: Request, explicit_actor_id: str | None = None) -> str:
    return _identity_from_request(
        request,
        (ADMIN_ACTOR_ID_HEADER, SESSION_USER_ID_HEADER),
        explicit_actor_id,
        fallback=LOCAL_ADMIN_ACTOR_ID,
    )


def _identity_from_request(
    request: Request,
    header_names: tuple[str, ...],
    explicit_value: str | None,
    *,
    fallback: str,
) -> str:
    for header_name in header_names:
        value = request.headers.get(header_name)
        normalized = (value or "").strip()
        if normalized:
            _ensure_trusted_auth_header(request)
            return normalized
    if not settings.auth_allow_local_fallback:
        raise HTTPException(status_code=401, detail="Auth session identity is required")
    normalized_explicit = (explicit_value or "").strip()
    if normalized_explicit:
        return normalized_explicit
    return fallback


def _ensure_trusted_auth_header(request: Request) -> None:
    expected = settings.auth_trusted_header_secret
    if not expected:
        return
    if request.headers.get(AUTH_SECRET_HEADER) == expected:
        return
    raise HTTPException(status_code=401, detail="Trusted auth header is required")


def _ensure_admin_write(request: Request, explicit_actor_id: str | None = None) -> str:
    actor_id = _resolve_admin_actor_id(request, explicit_actor_id)
    try:
        store.ensure_admin_permission(actor_id=actor_id)
    except AdminPermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return actor_id


async def _record_api_observation(
    *,
    request: Request,
    route: str | None,
    status_code: int,
    duration_ms: float,
    request_id: str,
    error_code: str | None = None,
    message: str | None = None,
) -> None:
    # The store writes these rows synchronously. Calling it directly from the async
    # middleware blocked the event loop on a database round-trip for the duration of
    # every single request, so concurrent requests queued behind each other's
    # logging instead of being served. Hand it to a worker thread instead.
    await run_in_threadpool(
        _record_api_observation_sync,
        request=request,
        route=route,
        status_code=status_code,
        duration_ms=duration_ms,
        request_id=request_id,
        error_code=error_code,
        message=message,
    )


def _record_api_observation_sync(
    *,
    request: Request,
    route: str | None,
    status_code: int,
    duration_ms: float,
    request_id: str,
    error_code: str | None = None,
    message: str | None = None,
) -> None:
    try:
        store.record_api_request(
            method=request.method,
            path=request.url.path,
            route=route,
            status_code=status_code,
            duration_ms=duration_ms,
            request_id=request_id,
            user_id=_request_user_id(request),
            client_host=request.client.host if request.client else None,
        )
        logger.info(
            "api_request method=%s path=%s status=%s duration_ms=%.3f request_id=%s",
            request.method,
            request.url.path,
            status_code,
            duration_ms,
            request_id,
        )
        if status_code >= 400:
            store.record_api_error(
                method=request.method,
                path=request.url.path,
                route=route,
                status_code=status_code,
                error_code=error_code or ERROR_CODES.get(status_code, "http_error"),
                message=message,
                request_id=request_id,
                payload={"query": dict(request.query_params)},
            )
    except Exception:
        logger.exception("api_observation_record_failed request_id=%s", request_id)


@app.get("/health")
def health() -> dict:
    return store.health()


@app.get("/universes/alpha")
def get_alpha() -> dict:
    return store.universe()


@app.get("/universes/alpha/reports/dynamic")
def get_alpha_dynamic_report(
    scope: str = Query(default="universe", pattern="^(universe|region|species|population)$"),
    limit: int = Query(default=12, ge=1, le=50),
    from_age: int | None = Query(default=None, ge=0, alias="fromAge"),
    to_age: int | None = Query(default=None, ge=0, alias="toAge"),
    region_id: str | None = Query(default=None, alias="regionId"),
    species_id: str | None = Query(default=None, alias="speciesId"),
) -> dict:
    if from_age is not None and to_age is not None and from_age > to_age:
        raise HTTPException(status_code=400, detail="fromAge must be less than or equal to toAge")
    if scope in {"region", "population"} and not region_id:
        raise HTTPException(status_code=400, detail="regionId is required for this report scope")
    if scope in {"species", "population"} and not species_id:
        raise HTTPException(status_code=400, detail="speciesId is required for this report scope")
    report = store.dynamic_report(
        scope=scope,
        limit=limit,
        from_age=from_age,
        to_age=to_age,
        region_id=region_id,
        species_id=species_id,
    )
    if report is None:
        raise HTTPException(status_code=404, detail="Report data not found")
    return report


@app.get("/universes/alpha/diagnostics")
def get_alpha_diagnostics() -> dict:
    """Criticality diagnostics behind /science.

    Public and unauthenticated, like the other read surfaces: this is the science
    the product is for, not an operator tool. The live probes cost ~8ms; the
    scale-free scan is not computed here — it is read back from the worker's last
    run. See docs/PERFORMANCE_LOOP.md.
    """
    return store.diagnostics()


@app.get("/universes/alpha/snapshots")
def get_alpha_snapshots(
    # Capped at the frame budget, not an arbitrary 100: compaction bounds all of
    # world history to that many frames, so this lets a client ask for the whole
    # timeline in one call. The old cap silently limited the scrubber to the
    # newest 100 ticks -- with a snapshot written every tick that was the last few
    # minutes of a universe millions of ticks old, and no amount of stored history
    # was reachable through it.
    limit: int = Query(default=50, ge=1, le=SNAPSHOT_FRAME_BUDGET),
    offset: int = Query(default=0, ge=0),
    from_age: int | None = Query(default=None, ge=0, alias="fromAge"),
    to_age: int | None = Query(default=None, ge=0, alias="toAge"),
) -> dict:
    if from_age is not None and to_age is not None and from_age > to_age:
        raise HTTPException(status_code=400, detail="fromAge must be less than or equal to toAge")
    return store.snapshots(
        limit=limit,
        offset=offset,
        from_age=from_age,
        to_age=to_age,
    )


@app.get("/universes/alpha/snapshots/latest")
def get_alpha_latest_snapshot() -> dict:
    return store.latest_snapshot()


@app.get("/universes/alpha/snapshots/{tick}/details")
def get_alpha_snapshot_details(tick: int) -> dict:
    details = store.snapshot_details(tick)
    if details is None:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return details


@app.get("/universes/alpha/landing")
def get_alpha_landing() -> dict:
    return store.landing()


@app.get("/universes/alpha/chronicle")
def get_alpha_chronicle(
    time_filter: str = Query(default="all", alias="timeFilter"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    cursor: str | None = Query(default=None),
) -> dict:
    return store.chronicle(
        time_filter=time_filter, limit=limit, offset=offset, cursor=cursor
    )


@app.get("/universes/alpha/events/stream")
async def stream_alpha_events(
    request: Request,
    last_event_id: str | None = Query(default=None, alias="lastEventId"),
) -> StreamingResponse:
    cursor = request.headers.get("last-event-id") or last_event_id

    async def event_generator():
        nonlocal cursor
        initial = store.event_stream(
            last_event_id=cursor,
            limit=EVENT_STREAM_BATCH_LIMIT,
        )
        cursor = initial["cursor"]
        yield _sse_event(
            "stream_status",
            {
                "status": "connected",
                "cursor": cursor,
                "missedCursor": initial["missedCursor"],
                "hasMore": initial["hasMore"],
                "universe": initial["universe"],
            },
        )

        for event in initial["events"]:
            cursor = event["id"]
            yield _sse_event("chronicle_event", event, event_id=event["id"])

        while True:
            if await request.is_disconnected():
                break
            snapshot = store.event_stream(
                last_event_id=cursor,
                limit=EVENT_STREAM_BATCH_LIMIT,
            )
            cursor = snapshot["cursor"]
            events = snapshot["events"]
            if events:
                for event in events:
                    cursor = event["id"]
                    yield _sse_event("chronicle_event", event, event_id=event["id"])
                continue
            yield _sse_event(
                "heartbeat",
                {
                    "status": "idle",
                    "cursor": cursor,
                    "ageYears": snapshot["universe"]["ageYears"],
                    "hasMore": snapshot["hasMore"],
                },
            )
            await asyncio.sleep(EVENT_STREAM_POLL_SECONDS)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/universes/alpha/regions")
def get_alpha_regions(mode: str = "life") -> dict:
    return store.regions(mode=mode)


@app.get("/me/identity")
def get_my_identity(
    request: Request,
    observer_user_id: str = Query(default=LOCAL_OBSERVER_USER_ID, alias="observerUserId"),
    catalyst_user_id: str = Query(default=LOCAL_CATALYST_USER_ID, alias="catalystUserId"),
    admin_actor_id: str = Query(default=LOCAL_ADMIN_ACTOR_ID, alias="adminActorId"),
    region_id: str | None = Query(default=None, alias="regionId"),
) -> dict:
    try:
        return store.identity_context(
            observer_user_id=_resolve_observer_user_id(request, observer_user_id),
            catalyst_user_id=_resolve_catalyst_user_id(request, catalyst_user_id),
            admin_actor_id=_resolve_admin_actor_id(request, admin_actor_id),
            region_id=region_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/me/follows")
def get_my_follows(
    request: Request,
    user_id: str = Query(default=LOCAL_OBSERVER_USER_ID, alias="userId"),
) -> dict:
    try:
        return store.observer_follows(user_id=_resolve_observer_user_id(request, user_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/me/follows/regions/{region_id}")
def post_follow_region(
    region_id: str,
    identity: ObserverIdentityRequest,
    request: Request,
) -> dict:
    try:
        result = store.follow_entity(
            user_id=_resolve_observer_user_id(request, identity.user_id),
            entity_type="region",
            entity_id=region_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Region not found")
    return result


@app.delete("/me/follows/regions/{region_id}")
def delete_follow_region(
    region_id: str,
    request: Request,
    user_id: str = Query(default=LOCAL_OBSERVER_USER_ID, alias="userId"),
) -> dict:
    try:
        result = store.unfollow_entity(
            user_id=_resolve_observer_user_id(request, user_id),
            entity_type="region",
            entity_id=region_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Region not found")
    return result


@app.post("/me/follows/species/{species_id}")
def post_follow_species(
    species_id: str,
    identity: ObserverIdentityRequest,
    request: Request,
) -> dict:
    try:
        result = store.follow_entity(
            user_id=_resolve_observer_user_id(request, identity.user_id),
            entity_type="species",
            entity_id=species_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Species not found")
    return result


@app.delete("/me/follows/species/{species_id}")
def delete_follow_species(
    species_id: str,
    request: Request,
    user_id: str = Query(default=LOCAL_OBSERVER_USER_ID, alias="userId"),
) -> dict:
    try:
        result = store.unfollow_entity(
            user_id=_resolve_observer_user_id(request, user_id),
            entity_type="species",
            entity_id=species_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Species not found")
    return result


@app.get("/me/notifications")
def get_my_notifications(
    request: Request,
    user_id: str = Query(default=LOCAL_OBSERVER_USER_ID, alias="userId"),
    unread_only: bool = Query(default=False, alias="unreadOnly"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict:
    try:
        return store.notifications(
            user_id=_resolve_observer_user_id(request, user_id),
            unread_only=unread_only,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/me/notifications/{notification_id}/read")
def post_notification_read(
    notification_id: str,
    identity: ObserverIdentityRequest,
    request: Request,
) -> dict:
    try:
        result = store.mark_notification_read(
            user_id=_resolve_observer_user_id(request, identity.user_id),
            notification_id=notification_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return result


@app.post("/me/notifications/read-all")
def post_notifications_read_all(
    identity: ObserverIdentityRequest,
    request: Request,
) -> dict:
    try:
        return store.mark_all_notifications_read(
            user_id=_resolve_observer_user_id(request, identity.user_id),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/analytics/events")
def post_analytics_event(request: AnalyticsEventRequest) -> dict:
    try:
        return store.track_product_event(
            event_name=request.event_name,
            user_id=request.user_id,
            session_id=request.session_id,
            subject_type=request.subject_type,
            subject_id=request.subject_id,
            source=request.source,
            metadata=request.metadata,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/me/catalyst/status")
def get_my_catalyst_status(
    request: Request,
    user_id: str = Query(default=LOCAL_CATALYST_USER_ID, alias="userId"),
    region_id: str | None = Query(default=None, alias="regionId"),
) -> dict:
    try:
        return store.catalyst_status(
            user_id=_resolve_catalyst_user_id(request, user_id),
            region_id=region_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/me/catalyst/actions")
def get_my_catalyst_actions(
    request: Request,
    user_id: str = Query(default=LOCAL_CATALYST_USER_ID, alias="userId"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict:
    try:
        return store.catalyst_actions(
            user_id=_resolve_catalyst_user_id(request, user_id),
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/me/catalyst/actions/{action_id}")
def get_my_catalyst_action(
    action_id: str,
    request: Request,
    user_id: str = Query(default=LOCAL_CATALYST_USER_ID, alias="userId"),
) -> dict:
    try:
        result = store.catalyst_action_detail(
            action_id=action_id,
            user_id=_resolve_catalyst_user_id(request, user_id),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Catalyst action not found")
    return result


@app.get("/regions/{region_id}")
def get_region(region_id: str) -> dict:
    region = store.region_detail(region_id)
    if region is None:
        raise HTTPException(status_code=404, detail="Region not found")
    return region


@app.get("/regions/{region_id}/events")
def get_region_events(
    region_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    cursor: str | None = Query(default=None),
) -> dict:
    events = store.region_events(region_id, limit=limit, offset=offset, cursor=cursor)
    if events is None:
        raise HTTPException(status_code=404, detail="Region not found")
    return events


@app.get("/species")
def get_species() -> dict:
    return store.species_list()


@app.get("/species/{species_id}")
def get_species_detail(species_id: str) -> dict:
    species = store.species_detail(species_id)
    if species is None:
        raise HTTPException(status_code=404, detail="Species not found")
    return species


@app.get("/species/{species_id}/forecast")
def get_species_forecast(species_id: str) -> dict:
    forecast = store.species_forecast(species_id)
    if forecast is None:
        raise HTTPException(status_code=404, detail="Species not found")
    return forecast


@app.get("/species/{species_id}/events")
def get_species_events(
    species_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    cursor: str | None = Query(default=None),
) -> dict:
    events = store.species_events(species_id, limit=limit, offset=offset, cursor=cursor)
    if events is None:
        raise HTTPException(status_code=404, detail="Species not found")
    return events


@app.post("/catalyst/actions")
def post_catalyst_action(payload: CatalystActionRequest, request: Request) -> dict:
    try:
        return store.catalyst_action(
            region_id=payload.region_id,
            action_type=payload.action_type,
            user_id=_resolve_catalyst_user_id(request, payload.user_id),
        )
    except (CatalystLimitError, CatalystCooldownError) as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except CatalystPermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AlphaStateConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/admin/simulate")
def post_admin_simulate(
    request: Request,
    ticks: int = Query(default=1, ge=1, le=500),
    actor_id: str = Query(default=LOCAL_ADMIN_ACTOR_ID, alias="actorId"),
) -> dict:
    _ensure_admin_write(request, actor_id)
    try:
        return store.advance(ticks=ticks)
    except AlphaStateConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/admin/simulation/health")
def get_admin_simulation_health() -> dict:
    health = store.simulation_health()
    stale_seconds = health.get("workerStaleSeconds")
    worker = health.get("worker")
    worker_running = bool(worker) and worker.get("status") == "running"
    worker_stale = (
        stale_seconds is not None and stale_seconds > settings.worker_stale_seconds
    )
    if not worker or stale_seconds is None:
        worker_state = "unknown"
    elif worker.get("status") == "error":
        worker_state = "error"
    elif worker_stale:
        worker_state = "stale"
    elif worker_running:
        worker_state = "healthy"
    else:
        worker_state = "stopped"
    health["operations"] = {
        "env": settings.env,
        "destructiveOpsAllowed": settings.allow_destructive_ops,
        "workerStaleThresholdSeconds": settings.worker_stale_seconds,
        "workerStale": worker_stale,
        "workerState": worker_state,
    }
    return health


@app.get("/admin/observability/summary")
def get_admin_observability_summary() -> dict:
    return store.observability_summary()


@app.get("/admin/observability/requests")
def get_admin_observability_requests(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict:
    return store.observability_requests(limit=limit, offset=offset)


@app.get("/admin/observability/errors")
def get_admin_observability_errors(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict:
    return store.observability_errors(limit=limit, offset=offset)


@app.get("/admin/observability/worker-events")
def get_admin_observability_worker_events(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict:
    return store.observability_worker_events(limit=limit, offset=offset)


@app.get("/admin/analytics/events")
def get_admin_analytics_events(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict:
    return store.analytics_events(limit=limit, offset=offset)


@app.get("/admin/simulation/controls")
def get_admin_simulation_controls() -> dict:
    return store.simulation_controls()


@app.post("/admin/simulation/batches")
def post_admin_simulation_batch(payload: AdminSimulationBatchRequest, request: Request) -> dict:
    actor_id = _ensure_admin_write(request, payload.actor_id)
    try:
        return store.run_simulation_batch(
            ticks=payload.ticks,
            actor_id=actor_id,
            reason=payload.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AlphaStateConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/admin/simulation/reset")
def post_admin_simulation_reset(payload: AdminSimulationResetRequest, request: Request) -> dict:
    actor_id = _ensure_admin_write(request, payload.actor_id)
    if not settings.allow_destructive_ops:
        raise HTTPException(
            status_code=403,
            detail=(
                "Destructive simulation reset is disabled. "
                "Set EVOVERSE_ALLOW_DESTRUCTIVE_OPS=true to enable."
            ),
        )
    try:
        return store.reset_simulation(
            actor_id=actor_id,
            reason=payload.reason,
            seed=payload.seed,
            boot_ticks=payload.boot_ticks,
            preserve_user_state=payload.preserve_user_state,
            confirm_reset=payload.confirm_reset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AlphaStateConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/admin/simulation/runs")
def get_admin_simulation_runs(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict:
    return store.simulation_runs(limit=limit, offset=offset)


@app.post("/admin/catalyst/users/{user_id}/role")
def post_admin_catalyst_user_role(
    user_id: str,
    payload: CatalystRoleRequest,
    request: Request,
) -> dict:
    granted_by = _ensure_admin_write(request, payload.granted_by)
    try:
        return store.grant_catalyst_role(
            user_id=user_id,
            role=payload.role,
            status=payload.status,
            granted_by=granted_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/admin/simulation/rules")
def get_admin_simulation_rules() -> dict:
    return store.simulation_rules()


@app.post("/admin/simulation/rules/validate")
def post_admin_simulation_rules_validate(
    payload: SimulationRulesChangeRequest,
    request: Request,
) -> dict:
    actor_id = _ensure_admin_write(request, payload.actor_id)
    return store.validate_simulation_rules(
        payload.rules,
        actor_id=actor_id,
        reason=payload.reason,
    )


@app.post("/admin/simulation/rules/apply")
def post_admin_simulation_rules_apply(payload: SimulationRulesChangeRequest, request: Request) -> dict:
    actor_id = _ensure_admin_write(request, payload.actor_id)
    try:
        return store.apply_simulation_rules(
            payload.rules,
            actor_id=actor_id,
            reason=payload.reason,
        )
    except RuleConfigValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.response) from exc


@app.post("/admin/simulation/rules/rollback")
def post_admin_simulation_rules_rollback(
    payload: SimulationRulesRollbackRequest,
    request: Request,
) -> dict:
    actor_id = _ensure_admin_write(request, payload.actor_id)
    try:
        return store.rollback_simulation_rules(
            actor_id=actor_id,
            reason=payload.reason,
            target_revision=payload.target_revision,
        )
    except RuleConfigRollbackError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/admin/simulation/rules/audit")
def get_admin_simulation_rules_audit(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict:
    return store.simulation_rules_audit(limit=limit, offset=offset)


@app.get("/admin/simulation/rules/revisions")
def get_admin_simulation_rules_revisions(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict:
    return store.simulation_rules_revisions(limit=limit, offset=offset)
