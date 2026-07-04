import { NextRequest, NextResponse } from "next/server";
import {
  AUTH_OAUTH_STATE_COOKIE,
  AUTH_SESSION_PROVIDER_COOKIE,
  AUTH_SESSION_USER_COOKIE,
  publicOrigin
} from "@/lib/authSession";

export async function GET(request: NextRequest) {
  const response = NextResponse.redirect(new URL("/auth?status=signed-out", publicOrigin(request)));
  response.cookies.delete(AUTH_SESSION_USER_COOKIE);
  response.cookies.delete(AUTH_SESSION_PROVIDER_COOKIE);
  response.cookies.delete(AUTH_OAUTH_STATE_COOKIE);
  return response;
}
