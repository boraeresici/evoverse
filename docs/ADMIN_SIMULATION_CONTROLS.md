# Admin Simulation Controls API

Admin simulation controls are intentionally separate from public Alpha surfaces. Public UI must not expose raw ticks, debug counters, seed reset tooling, or worker diagnostics.

Admin write endpoints require an active `admin` role. During Alpha, `local-admin` is the development fallback actor. Session/header identity takes precedence over legacy body/query `actorId`:

- `x-evoverse-admin-id`
- `x-evoverse-user-id`

## `GET /admin/simulation/controls`

Response model: `admin_simulation_controls_v1`

Returns the current admin-only control surface:

- current Alpha state summary.
- manual batch tick limits.
- seed reset requirements.
- worker heartbeat state.
- rules reload/governance state.
- admin-only debug metadata.

Important contract:

```json
{
  "model": "admin_simulation_controls_v1",
  "mode": {
    "runtime": "api_manual_batch",
    "publicTickExposure": "hidden"
  },
  "controls": {
    "batchTick": {
      "enabled": true,
      "minTicks": 1,
      "maxTicks": 500
    },
    "seedReset": {
      "enabled": true,
      "requiresConfirmReset": true
    }
  },
  "debug": {
    "visibility": "admin_only"
  }
}
```

## `POST /admin/simulation/batches`

Runs a bounded manual batch tick from the API.

Requires active Admin role.

Body:

```json
{
  "ticks": 24,
  "actorId": "local-admin",
  "reason": "Low activity catch-up"
}
```

Response model: `admin_simulation_batch_v1`

The response includes:

- admin run ledger row.
- before/after state summaries.
- refreshed health.
- refreshed controls.

`ticks` must be between `1` and `500`. Larger simulation runs belong in worker or benchmark tooling.

## `POST /admin/simulation/reset`

Rebuilds Alpha from a seed and boot tick count.

Requires active Admin role.

Body:

```json
{
  "actorId": "local-admin",
  "reason": "Rebuild Alpha for a controlled demo",
  "seed": 4211,
  "bootTicks": 96,
  "preserveUserState": true,
  "confirmReset": true
}
```

Response model: `admin_simulation_reset_v1`

`confirmReset` must be true. This endpoint resets simulation state and preserves governance state:

- rules revisions and audit logs stay.
- Catalyst roles stay.
- admin run ledger stays.

When `preserveUserState` is true, observer follows and notification reads stay. Simulation events, snapshots, active Catalyst actions, and Catalyst action logs are reset.

## `GET /admin/simulation/runs`

Query:

- `limit`, default `50`
- `offset`, default `0`

Response model: `admin_simulation_runs_v1`

Returns the admin run ledger for manual batch and reset operations.

## Legacy Endpoint

`POST /admin/simulate?ticks=1&actorId=local-admin` remains available as a backward-compatible health shortcut and now requires active Admin role. New admin surfaces should use `POST /admin/simulation/batches` because it records actor, reason, before/after, and run history.

## Editable Rules Admin UI

The read-only rules screen at `/admin/config` is now a writable editor backed by the existing validation/audit/rollback endpoints. `GET /admin/simulation/rules` reports the editable surface:

- `mode: "editable"`, `governance.uiEditable: true`, `governance.writeSurface: "api_and_admin_ui"`.
- `revision` and `rulesHash` describe the active applied config.

### Frontend flow

- The browser never calls the admin mutation endpoints directly and never carries `actorId`. Client mutations go through same-origin BFF routes that forward trusted session headers (`lib/serverApi.ts`), consistent with the same-origin BFF cleanup:
  - `POST /api/admin/rules/validate` → `POST /admin/simulation/rules/validate`
  - `POST /api/admin/rules/apply` → `POST /admin/simulation/rules/apply`
  - `POST /api/admin/rules/rollback` → `POST /admin/simulation/rules/rollback`
  - `GET /api/admin/rules/history` → fans out to `/admin/simulation/rules/audit` + `/rules/revisions` for post-mutation refresh.
- The editor (`components/RulesEditor.tsx`) sends only changed fields as a partial `rules` payload; the backend merges against the active config.
- Draft → Validate → Apply → Rollback: the user edits numeric fields, the change preview shows `old → new` per field, Validate surfaces backend errors/warnings, Apply persists a new revision, and Rollback restores a prior revision (latest or a chosen `targetRevision`).
- The editor is gated by `capabilities.admin.canUseAdmin`; non-admin identities see inputs disabled with a gate notice. All three backend endpoints independently enforce the active `admin` role, so the gate is defense-in-depth, not the security boundary.

### Risky-change warnings and preview

- Client heuristic flags risky changes before apply: collapse/recovery/forced/extinction thresholds, catalyst daily-quota changes, changes larger than 50% relative to the current value, and enabling a previously-zero rule.
- When risky changes are present, Apply is blocked until the admin confirms an explicit acknowledgement checkbox.
- Backend semantic `warnings` (e.g. forced collapse above threshold) are surfaced in the validation panel alongside hard errors.

### Hot reload strategy

- `reloadStrategy` is shown after apply/rollback: API hot-reloads the active rules in place; the worker reloads its repository config before its next step (`pending_next_step`); `restartRequired` is `false`. Validation-only requests report `not_applied`.

## Migration

- `006_admin_simulation_controls`
