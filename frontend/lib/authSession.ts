import { cookies } from "next/headers";
import type { NextRequest } from "next/server";

/**
 * The externally-visible origin. Behind a reverse proxy (Traefik/Cloudflare) the
 * server sees an internal host (e.g. 0.0.0.0:3000), so auth redirects must be
 * built from the forwarded headers instead of request.url.
 */
export function publicOrigin(request: NextRequest): string {
  const proto = request.headers.get("x-forwarded-proto")?.split(",")[0]?.trim();
  const host =
    request.headers.get("x-forwarded-host")?.split(",")[0]?.trim() ||
    request.headers.get("host")?.trim();
  if (host) {
    return `${proto || "https"}://${host}`;
  }
  return request.nextUrl.origin;
}

export const AUTH_SESSION_USER_COOKIE = "evoverse_session_user";
export const AUTH_SESSION_PROVIDER_COOKIE = "evoverse_session_provider";
export const AUTH_OAUTH_STATE_COOKIE = "evoverse_oauth_state";

export type ServerAuthSession = {
  userId: string;
  provider: string;
};

export type AuthRuntimeConfig = {
  provider: string;
  googleClientId: string;
  googleClientSecret: string;
  googleRedirectUri: string;
  googleClientConfigured: boolean;
  googleSecretConfigured: boolean;
  googleReady: boolean;
  trustedHeaderConfigured: boolean;
};

type GoogleIdTokenPayload = {
  aud: string | string[];
  email?: string;
  email_verified?: boolean;
  exp?: number;
  name?: string;
  picture?: string;
  sub: string;
};

export async function getServerAuthSession(): Promise<ServerAuthSession | null> {
  const cookieStore = await cookies();
  const userId = cookieStore.get(AUTH_SESSION_USER_COOKIE)?.value.trim();
  if (!userId) {
    return null;
  }
  return {
    userId,
    provider: cookieStore.get(AUTH_SESSION_PROVIDER_COOKIE)?.value.trim() || "google"
  };
}

export async function getTrustedSessionHeaders(): Promise<Record<string, string>> {
  const session = await getServerAuthSession();
  if (!session) {
    return {};
  }
  const headers: Record<string, string> = {
    "x-evoverse-user-id": session.userId
  };
  const secret = process.env.EVOVERSE_AUTH_TRUSTED_HEADER_SECRET;
  if (secret) {
    headers["x-evoverse-auth-secret"] = secret;
  }
  return headers;
}

export function getAuthRuntimeConfig(origin = ""): AuthRuntimeConfig {
  const googleClientId =
    process.env.EVOVERSE_GOOGLE_CLIENT_ID ?? process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID ?? "";
  const googleClientSecret = process.env.EVOVERSE_GOOGLE_CLIENT_SECRET ?? "";
  const googleRedirectUri =
    process.env.EVOVERSE_GOOGLE_REDIRECT_URI ||
    (origin ? `${origin}/api/auth/callback/google` : "");

  return {
    provider:
      process.env.NEXT_PUBLIC_AUTH_PROVIDER ?? process.env.EVOVERSE_AUTH_PROVIDER ?? "local",
    googleClientId,
    googleClientSecret,
    googleRedirectUri,
    googleClientConfigured: Boolean(googleClientId),
    googleSecretConfigured: Boolean(googleClientSecret),
    googleReady: Boolean(googleClientId && googleClientSecret && googleRedirectUri),
    trustedHeaderConfigured: Boolean(process.env.EVOVERSE_AUTH_TRUSTED_HEADER_SECRET)
  };
}

export function parseGoogleIdToken(idToken: string, clientId: string): GoogleIdTokenPayload {
  const [, payloadSegment] = idToken.split(".");
  if (!payloadSegment) {
    throw new Error("Google id token payload is missing");
  }
  const payload = JSON.parse(decodeBase64Url(payloadSegment)) as GoogleIdTokenPayload;
  const audience = Array.isArray(payload.aud) ? payload.aud : [payload.aud];
  if (!audience.includes(clientId)) {
    throw new Error("Google id token audience mismatch");
  }
  if (payload.exp && payload.exp * 1000 < Date.now()) {
    throw new Error("Google id token expired");
  }
  if (!payload.sub) {
    throw new Error("Google id token subject is missing");
  }
  return payload;
}

export function googlePayloadToUserId(payload: GoogleIdTokenPayload): string {
  if (payload.email && payload.email_verified !== false) {
    return payload.email.toLowerCase();
  }
  return `google:${payload.sub}`;
}

function decodeBase64Url(value: string): string {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  const padding = (4 - (normalized.length % 4)) % 4;
  return Buffer.from(normalized.padEnd(normalized.length + padding, "="), "base64").toString(
    "utf-8"
  );
}
