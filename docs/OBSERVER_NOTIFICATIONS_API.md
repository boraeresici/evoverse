# Observer Follows and Notifications API

## Scope

This is the first backend foundation for Observer accounts. Google Auth is still provider-adapter work, but session/header identity resolution is active. In local development, endpoints accept legacy `userId` and default to `local-observer`.

## Follows

### `GET /me/follows`

Query:

- `userId`: optional, default `local-observer`

Response model: `observer_follows_v1`

```json
{
  "model": "observer_follows_v1",
  "user": {
    "id": "local-observer",
    "mode": "local_observer",
    "auth": "deferred"
  },
  "follows": {
    "regions": [],
    "species": []
  },
  "counts": {
    "regions": 0,
    "species": 0,
    "total": 0
  }
}
```

### `POST /me/follows/regions/{regionId}`

Body:

```json
{
  "userId": "local-observer"
}
```

Adds a region follow. Duplicate follow requests are idempotent.

### `POST /me/follows/species/{speciesId}`

Body:

```json
{
  "userId": "local-observer"
}
```

Adds a species follow. Duplicate follow requests are idempotent.

### `DELETE /me/follows/regions/{regionId}`

Query:

- `userId`: optional, default `local-observer`

### `DELETE /me/follows/species/{speciesId}`

Query:

- `userId`: optional, default `local-observer`

## Notifications

### `GET /me/notifications`

Query:

- `userId`: optional, default `local-observer`
- `unreadOnly`: optional boolean, default `false`
- `limit`: optional, 1-100
- `offset`: optional

Response model: `observer_notifications_v1`

Notification kinds:

- `followed_region_event`
- `followed_species_event`
- `catalyst_action`
- `catalyst_downstream_event`

Notifications are projected from the append-only event log and user follows. Read state is persisted separately.

### `POST /me/notifications/{notificationId}/read`

Body:

```json
{
  "userId": "local-observer"
}
```

Marks a projected notification as read. Unknown notification ids return `404`.

### `POST /me/notifications/read-all`

Body:

```json
{
  "userId": "local-observer"
}
```

Marks every currently-unread projected notification for the user as read in one call. Response:

```json
{
  "markedRead": true,
  "markedCount": 9,
  "unreadCount": 0,
  "user": { "id": "local-observer", "mode": "local_observer", "auth": "deferred" }
}
```

Idempotent: a repeat call returns `markedCount: 0`. As with single mark-read, identity comes from the session/header bridge; the client BFF route `/api/observer/notifications/read-all` forwards trusted session headers and the browser sends no `userId`.

## Engagement: Following Digest

The `/notifications` page renders a client-side "Following Digest" above the raw inbox. It is composed from existing endpoints (`/me/follows` + `/me/notifications`), so no new aggregation endpoint is required:

- Events are categorized with the shared `frontend/lib/speciesEvents.ts` classifier (emergence, major mutation, extinction, decline, collapse, resource shift, catalyst).
- `frontend/lib/digest.ts` groups notifications per followed region/species, computes unread counts, per-category counts, a headline, and cross-entity "highlights" (important events only) as the reason-to-return.
- Windows are `Daily` / `Weekly` / `All time`, derived from a single `AGE_PER_DAY` world-age span constant. The literal tick→calendar mapping is still an open product decision (world-age conversion), so the cadence is a tunable placeholder rather than a wall-clock date.
- Notification quality: the inbox supports an unread filter, category-chip filtering, per-event category badges/tones, and a "Mark all read" action backed by `read-all`.
- Email digests remain out of scope for this package.

## Persistence

Tables:

- `observer_follows`: persistent user follow state.
- `notification_reads`: per-user read state for deterministic projected notifications.

Migration:

- `004_observer_notifications`

## Auth Upgrade Path

When Google Auth lands, `userId` should be derived from the session and passed through the existing identity bridge. The response model can stay stable. If `EVOVERSE_AUTH_ALLOW_LOCAL_FALLBACK=false`, requests without session/header identity receive HTTP `401`.
