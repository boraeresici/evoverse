export const LOCAL_IDENTITY = {
  observerUserId: "local-observer",
  catalystUserId: "local-catalyst",
  adminActorId: "local-admin"
} as const;

export const OBSERVER_USER_ID = LOCAL_IDENTITY.observerUserId;
export const CATALYST_USER_ID = LOCAL_IDENTITY.catalystUserId;
export const ADMIN_ACTOR_ID = LOCAL_IDENTITY.adminActorId;

export const PUBLIC_AUTH_PROVIDER = process.env.NEXT_PUBLIC_AUTH_PROVIDER ?? "local";
export const PUBLIC_GOOGLE_CLIENT_CONFIGURED = Boolean(process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID);

export const AUTH_GATE_COPY = {
  provider: PUBLIC_AUTH_PROVIDER === "google" ? "Google Auth" : "Local Alpha",
  nextProvider: "Google Auth",
  catalystGate: "Invite or role gate first",
  subscription: "Deferred",
  googleClient: PUBLIC_GOOGLE_CLIENT_CONFIGURED ? "Configured" : "Pending"
} as const;
