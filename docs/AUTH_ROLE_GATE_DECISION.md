# Evoverse Auth and Role Gate Decision

## Decision

Alpha keeps a local identity bridge before production authentication:

- Observer: `local-observer`
- Catalyst: `local-catalyst`
- Admin: `local-admin`

Google Auth is the target provider, but it should not block the current Alpha experience. The current implementation exposes the same role shape that Google Auth will later feed.

## Environment Contract

Backend:

- `EVOVERSE_AUTH_PROVIDER`: `local` or `google`.
- `EVOVERSE_AUTH_ALLOW_LOCAL_FALLBACK`: `true` in local development; should be `false` in production.
- `EVOVERSE_AUTH_BOOTSTRAP_ADMINS`: comma-separated user ids granted initial `admin`.
- `EVOVERSE_AUTH_BOOTSTRAP_CATALYSTS`: comma-separated user ids granted initial `catalyst`.
- `EVOVERSE_AUTH_TRUSTED_HEADER_SECRET`: shared BFF/API secret required before session identity headers are accepted.
- `EVOVERSE_GOOGLE_CLIENT_ID`: Google OAuth client id.
- `EVOVERSE_GOOGLE_CLIENT_SECRET`: Google OAuth client secret.
- `EVOVERSE_GOOGLE_REDIRECT_URI`: optional explicit Google OAuth callback URL. Defaults to `/api/auth/callback/google` on the frontend origin.

Frontend:

- `NEXT_PUBLIC_AUTH_PROVIDER`: public provider label.
- `NEXT_PUBLIC_GOOGLE_CLIENT_ID`: public Google OAuth client id.

## Why This Comes First

Evoverse already has behavior that depends on identity:

- Observer follows and notifications.
- Catalyst actions, quotas, cooldowns, and result tracking.
- Admin simulation controls and rules governance.
- Product analytics user attribution.

Jumping directly into Google Auth would mix provider setup, UI session state, role policy, and existing endpoint cleanup in one risky package. The safer bridge is:

1. Make current local identities explicit and centralized.
2. Expose a single current identity/role context.
3. Keep Catalyst invite/role gate active.
4. Defer subscription checks until after real authenticated users exist.

## Current Contract

`GET /me/identity` returns `identity_context_v1`.

The payload includes:

- `auth`: local provider, deferred Google Auth status, and source.
- `auth.localFallback`: whether explicit local ids are accepted when no session/header identity exists.
- `auth.sessionStrategy`: `local_bridge` or `trusted_header`.
- `auth.trustedHeaderRequired`: whether backend session headers require `x-evoverse-auth-secret`.
- `auth.googleClientConfigured`: whether the backend has a Google client id configured.
- `users.observer`: current Observer identity.
- `users.catalyst`: current Catalyst identity and role status.
- `users.admin`: current Admin actor and role status.
- `capabilities.observer`: follow and notification permission.
- `capabilities.catalyst`: Catalyst permission, quotas, cooldowns, and optional region scope.
- `capabilities.admin`: admin permission signal.
- `roleGate`: current policy labels for Observer, Catalyst, Admin, and subscription.

## Product Policy

- Observer access stays open in Alpha.
- Catalyst access is invite/role gated first.
- Admin access requires an active admin role.
- Subscription is deferred.
- Google Auth will later replace explicit local IDs with session-derived identity.
- Bootstrap invite lists grant the first Admin and Catalyst roles through the existing `catalyst_user_roles` store.

## Implementation Notes

- `local-catalyst` and `local-admin` are persisted as baseline roles.
- Guest Catalyst users receive `canUseCatalyst: false` with `catalyst_role_required`.
- Guest Admin actors receive `canUseAdmin: false` with `admin_role_required`.
- Session/header identity shape is active for API requests:
  - `x-evoverse-user-id` is the generic session-derived user id placeholder.
  - `x-evoverse-observer-id`, `x-evoverse-catalyst-id`, and `x-evoverse-admin-id` can override role-specific identities.
  - Header identity takes precedence over legacy query/body `userId` and `actorId` fields.
- Existing query/body `userId` and `actorId` fields remain for compatibility and development fallback.
- If `EVOVERSE_AUTH_ALLOW_LOCAL_FALLBACK=false`, a request without session/header identity receives HTTP `401`.
- If `EVOVERSE_AUTH_TRUSTED_HEADER_SECRET` is set, session/header identity is accepted only when `x-evoverse-auth-secret` matches that secret. This is the production-leaning BFF/proxy boundary; browsers should not send this secret directly.
- Admin write endpoints require an active `admin` role. Guest session headers receive HTTP `403`.
- Frontend `/auth` exposes the current Auth runtime state and routes:
  - `/api/auth/google` starts Google OAuth.
  - `/api/auth/callback/google` exchanges the code, validates the Google id token audience/expiry, and stores the session user id in an HTTP-only cookie.
  - `/api/auth/logout` clears the local session cookie.
- Frontend server-side API fetches read that HTTP-only session cookie and send `x-evoverse-user-id` plus `x-evoverse-auth-secret` to the backend when configured.

## Client Mutation Identity Cleanup

Client components no longer call the backend mutation endpoints directly and no longer carry local `userId`/`actorId` from the browser:

- Follow/unfollow, notification mark-read, and catalyst action submit now POST to same-origin BFF routes under `frontend/app/api/*`:
  - `POST /api/observer/follow` — body `{ entityId, entityType, follow }` → backend `POST`/`DELETE /me/follows/{regions|species}/{id}`.
  - `POST /api/observer/notifications/read` — body `{ notificationId }` → backend `POST /me/notifications/{id}/read`.
  - `POST /api/catalyst/action` — body `{ regionId, actionType }` → backend `POST /catalyst/actions`.
- The BFF routes resolve identity server-side via `getTrustedSessionHeaders` (`lib/serverApi.ts` → `forwardToBackend`): the session cookie produces `x-evoverse-user-id` plus `x-evoverse-auth-secret` when configured. The browser sends no identity at all.
- In local development (`EVOVERSE_AUTH_ALLOW_LOCAL_FALLBACK=true`, no session) the trusted headers are empty and the backend resolves its local `local-observer`/`local-catalyst` defaults, preserving the current dev experience.
- BFF routes validate required fields and short-circuit with HTTP `400` before any backend call; backend status/payload (e.g. `403`/`404`/`429`) is mirrored back to the client verbatim.
- `EVOVERSE_API_URL` (server-only) is honored ahead of `NEXT_PUBLIC_API_URL` for the BFF → backend hop, keeping the backend origin off the browser when desired.
- Read-only client streams (e.g. live chronicle SSE) remain direct reads with no identity and are out of scope for mutation cleanup.

### Production smoke scenario

With `EVOVERSE_AUTH_ALLOW_LOCAL_FALLBACK=false` and `EVOVERSE_AUTH_TRUSTED_HEADER_SECRET` set:

- A signed-in browser session triggers a BFF route; the route forwards `x-evoverse-user-id` + `x-evoverse-auth-secret`, and the backend accepts the trusted identity.
- A browser cannot reach the backend mutation endpoints directly: without the trusted secret the backend returns `401`, and without a session cookie the BFF forwards no identity so the backend returns `401`.
- The Google callback signs a real credential into the HTTP-only session cookie; the same cookie then authorizes follow/notification/catalyst mutations through the BFF, validating the invite-gated start flow end to end.

## Next Step

After this cleanup, remaining follow-ups:

- map authenticated users to persisted Observer/Catalyst/Admin roles through invite bootstrap;
- keep subscription checks deferred until production Auth is stable.
