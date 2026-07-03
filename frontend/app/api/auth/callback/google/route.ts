import { NextRequest, NextResponse } from "next/server";
import {
  AUTH_OAUTH_STATE_COOKIE,
  AUTH_SESSION_PROVIDER_COOKIE,
  AUTH_SESSION_USER_COOKIE,
  getAuthRuntimeConfig,
  googlePayloadToUserId,
  parseGoogleIdToken
} from "@/lib/authSession";

type GoogleTokenResponse = {
  error?: string;
  id_token?: string;
};

export async function GET(request: NextRequest) {
  const error = request.nextUrl.searchParams.get("error");
  if (error) {
    return redirectToAuth(request, `google-${error}`);
  }

  const code = request.nextUrl.searchParams.get("code");
  const state = request.nextUrl.searchParams.get("state");
  const expectedState = request.cookies.get(AUTH_OAUTH_STATE_COOKIE)?.value;
  if (!code || !state || !expectedState || state !== expectedState) {
    return redirectToAuth(request, "oauth-state-mismatch");
  }

  const config = getAuthRuntimeConfig(request.nextUrl.origin);
  if (!config.googleReady) {
    return redirectToAuth(request, "google-runtime-missing");
  }

  try {
    const tokenResponse = await fetch("https://oauth2.googleapis.com/token", {
      body: new URLSearchParams({
        client_id: config.googleClientId,
        client_secret: config.googleClientSecret,
        code,
        grant_type: "authorization_code",
        redirect_uri: config.googleRedirectUri
      }),
      headers: {
        "content-type": "application/x-www-form-urlencoded"
      },
      method: "POST"
    });
    const tokenPayload = (await tokenResponse.json()) as GoogleTokenResponse;
    if (!tokenResponse.ok || !tokenPayload.id_token) {
      throw new Error(tokenPayload.error || "Google token exchange failed");
    }

    const profile = parseGoogleIdToken(tokenPayload.id_token, config.googleClientId);
    const userId = googlePayloadToUserId(profile);
    const response = redirectToAuth(request, "signed-in");
    response.cookies.set(AUTH_SESSION_USER_COOKIE, userId, sessionCookieOptions(request));
    response.cookies.set(AUTH_SESSION_PROVIDER_COOKIE, "google", sessionCookieOptions(request));
    response.cookies.delete(AUTH_OAUTH_STATE_COOKIE);
    return response;
  } catch {
    return redirectToAuth(request, "google-session-failed");
  }
}

function redirectToAuth(request: NextRequest, status: string) {
  return NextResponse.redirect(new URL(`/auth?status=${encodeURIComponent(status)}`, request.url));
}

function sessionCookieOptions(request: NextRequest) {
  return {
    httpOnly: true,
    maxAge: 60 * 60 * 24 * 30,
    path: "/",
    sameSite: "lax" as const,
    secure: request.nextUrl.protocol === "https:"
  };
}
