# Realtime Event Stream

## Decision

Alpha Chronicle realtime delivery starts with Server-Sent Events.

SSE is enough for the current one-way requirement: backend publishes new simulation events, frontend appends them without polling. WebSocket can be revisited when Catalyst or collaborative observer flows need low-latency client-to-server interaction.

## Endpoint

`GET /universes/alpha/events/stream`

Query:

- `lastEventId`: optional event cursor. When present, the stream sends events after this id.

Headers:

- `Last-Event-ID`: optional SSE reconnect cursor. This takes precedence over `lastEventId`.

Response:

- `Content-Type: text/event-stream`
- `Cache-Control: no-cache`
- `Connection: keep-alive`

## Events

### `stream_status`

Sent once when the connection opens.

```json
{
  "status": "connected",
  "cursor": "evt-...",
  "missedCursor": false,
  "hasMore": false,
  "universe": {}
}
```

### `chronicle_event`

Sent for every new Chronicle event. The SSE `id` is the Chronicle event id.

```json
{
  "id": "evt-...",
  "eventType": "species_emerged",
  "eventLabel": "Species Emerged",
  "severity": 3,
  "worldAge": 4314,
  "title": "...",
  "summary": "...",
  "payloadSchemaVersion": 1,
  "payloadSchema": "event_payload.species_emerged.v1",
  "createdAt": "..."
}
```

### `heartbeat`

Sent when no new event is available during a poll cycle.

```json
{
  "status": "idle",
  "cursor": "evt-...",
  "ageYears": 4314,
  "hasMore": false
}
```

## Cursor Semantics

- No cursor means "start from the latest known event"; the first connection does not replay the entire Chronicle.
- Known cursor returns events after that cursor, oldest to newest.
- Unknown cursor returns a bounded recovery batch and marks `missedCursor: true`.
- Frontend deduplicates by event id and keeps the visible Chronicle bounded.

## Frontend Fallback

The Chronicle page uses `EventSource` when available. If the browser does not support it, the page falls back to the existing Chronicle API with a 10-second polling interval.
