# Catalyst API

Catalyst is invite/role gated in the Alpha backend. Google Auth and subscription checks are deferred; the current contract uses explicit local user ids and persisted role grants.

## Identity

- Default Catalyst user: `local-catalyst`
- Default admin user: `local-admin`
- Users without an active `catalyst` or `admin` role cannot trigger Catalyst actions.
- Current local identity and role context is exposed by `GET /me/identity`.
- Session/header identity takes precedence over legacy query/body ids.
- Product decision details: [`AUTH_ROLE_GATE_DECISION.md`](AUTH_ROLE_GATE_DECISION.md).

Session bridge headers:

- `x-evoverse-user-id`: generic session-derived user id placeholder.
- `x-evoverse-observer-id`: Observer-specific override.
- `x-evoverse-catalyst-id`: Catalyst-specific override.
- `x-evoverse-admin-id`: Admin actor override.

## `GET /me/identity`

Query:

- `observerUserId`, default `local-observer`
- `catalystUserId`, default `local-catalyst`
- `adminActorId`, default `local-admin`
- `regionId`, optional

Response model: `identity_context_v1`

This is the local Alpha bridge that will later be fed by Google Auth session identity. It returns Observer, Catalyst, and Admin users plus their current role-gate capabilities.

When a session/header identity is present, it wins over the query parameters above.

## `GET /me/catalyst/status`

Query:

- `userId`, default `local-catalyst`
- `regionId`, optional

Response model: `catalyst_capabilities_v1`

```json
{
  "model": "catalyst_capabilities_v1",
  "user": {
    "id": "local-catalyst",
    "mode": "local_catalyst",
    "auth": "deferred",
    "role": "catalyst",
    "status": "active"
  },
  "permission": {
    "canUseCatalyst": true,
    "reason": null
  },
  "quotas": [
    {
      "actionType": "energy_pulse",
      "dayKey": "2026-06-12",
      "limit": 3,
      "used": 0,
      "remaining": 3
    }
  ],
  "cooldowns": [],
  "regionId": "region-001"
}
```

## `POST /catalyst/actions`

Body:

```json
{
  "regionId": "region-001",
  "actionType": "energy_pulse",
  "userId": "local-catalyst"
}
```

Responses:

- `200`: accepted and influence initiated.
- `403`: user does not have an active Catalyst-capable role.
- `429`: daily quota or region cooldown blocked the action.

Accepted response model: `catalyst_action_result_v1`

Important fields:

- `accepted`: backward-compatible boolean.
- `status`: currently `accepted` on POST.
- `message`: user-facing action state, currently `Influence initiated`.
- `capabilities`: refreshed quotas and cooldowns after the action.
- `tracking`: result projection for the action, including source event and downstream events.

## `GET /me/catalyst/actions`

Query:

- `userId`, default `local-catalyst`
- `limit`, default `50`
- `offset`, default `0`

Response model: `catalyst_actions_v1`

Each action includes:

- source Catalyst event.
- downstream event count.
- up to 10 downstream events.
- status:
  - `influence_active`
  - `influence_initiated`
  - `influence_detected`

## `GET /me/catalyst/actions/{actionId}`

Returns one `catalyst_action_result_v1` projection for the requesting `userId`.

## `POST /admin/catalyst/users/{userId}/role`

Requires an active Admin actor. `grantedBy` remains the legacy body field, but `x-evoverse-admin-id` or `x-evoverse-user-id` overrides it when present.

Body:

```json
{
  "role": "catalyst",
  "status": "active",
  "grantedBy": "local-admin"
}
```

Supported roles:

- `catalyst`
- `admin`

Supported statuses:

- `active`
- `revoked`

## Persistence

- `catalyst_user_roles`: persisted invite/role gate.
- `catalyst_action_logs`: accepted action history and quota source.
- Downstream result tracking is projected from event payload metadata:
  - `catalyst_action_ids`
  - `catalyst_user_ids`
  - `catalyst_action_types`

Migration:

- `005_catalyst_roles_results`
