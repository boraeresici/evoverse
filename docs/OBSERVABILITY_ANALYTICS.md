# Observability and Analytics API

This package creates the first durable observability layer for Alpha. The goal is operational visibility without leaking debug data into public product screens.

## Backend Request Logging

Every HTTP request is observed by middleware and written to `api_request_logs`.

Captured fields:

- method
- path
- route
- status code
- duration in milliseconds
- request id
- optional user id from `userId` query or `x-evoverse-user-id`
- client host

Every response also gets an `X-Request-ID` header.

## Error Tracking

HTTP responses with status `>= 400` are written to `api_error_logs`.

Unhandled exceptions are recorded as `unhandled_exception` and then re-raised for FastAPI/Uvicorn to handle.

## Worker Run Events

Worker lifecycle events are written to `worker_run_events`.

Current event types:

- `start`
- `complete`
- `error`

Admin summary derives:

- starts
- completions
- crashes
- restarts

Restart count is currently `max(0, starts - 1)`.

## Product Analytics

Product analytics events are written to `product_analytics_events`.

Supported event names:

- `landing_view`
- `detail_view`
- `follow`
- `catalyst_action`
- `replay_interaction`

Automatic server-side events:

- `GET /universes/alpha/landing` records `landing_view`.
- `GET /regions/{id}` and `GET /species/{id}` record `detail_view`.
- Follow creation records `follow`.
- Accepted Catalyst actions record `catalyst_action`.

Client/manual events:

### `POST /analytics/events`

```json
{
  "eventName": "replay_interaction",
  "userId": "local-observer",
  "sessionId": "session-1",
  "subjectType": "universe",
  "subjectId": "alpha",
  "source": "client",
  "metadata": {
    "control": "step_forward"
  }
}
```

Response model: `product_analytics_event_v1`

## Admin Endpoints

### `GET /admin/observability/summary`

Response model: `observability_summary_v1`

Includes:

- request totals and status buckets.
- error totals and error-code buckets.
- worker lifecycle counts and latest heartbeat.
- product analytics counts and rates.

Analytics rates:

- `landingToDetailRate = detail_view / landing_view`
- `followRate = follow / detail_view`

### `GET /admin/observability/requests`

Response model: `api_request_logs_v1`

### `GET /admin/observability/errors`

Response model: `api_error_logs_v1`

### `GET /admin/observability/worker-events`

Response model: `worker_run_events_v1`

### `GET /admin/analytics/events`

Response model: `product_analytics_events_v1`

## Migration

- `007_observability_analytics`
