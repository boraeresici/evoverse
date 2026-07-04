import { NextRequest, NextResponse } from "next/server";
import { AUTH_OAUTH_STATE_COOKIE, getAuthRuntimeConfig, publicOrigin } from "@/lib/authSession";

export async function GET(request: NextRequest) {
  const origin = publicOrigin(request);
  const config = getAuthRuntimeConfig(origin);
  if (!config.googleClientConfigured) {
    return NextResponse.redirect(new URL("/auth?status=google-client-missing", origin));
  }

  const state = crypto.randomUUID();
  const authorizeUrl = new URL("https://accounts.google.com/o/oauth2/v2/auth");
  authorizeUrl.searchParams.set("client_id", config.googleClientId);
  authorizeUrl.searchParams.set("redirect_uri", config.googleRedirectUri);
  authorizeUrl.searchParams.set("response_type", "code");
  authorizeUrl.searchParams.set("scope", "openid email profile");
  authorizeUrl.searchParams.set("state", state);
  authorizeUrl.searchParams.set("include_granted_scopes", "true");

  const response = NextResponse.redirect(authorizeUrl);
  response.cookies.set(AUTH_OAUTH_STATE_COOKIE, state, {
    httpOnly: true,
    maxAge: 600,
    path: "/",
    sameSite: "lax",
    secure: origin.startsWith("https:")
  });
  return response;
}
