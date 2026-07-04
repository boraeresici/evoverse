import { getTrustedSessionHeaders } from "./authSession";

// `||` (not `??`) so an empty NEXT_PUBLIC_API_URL falls through to the default.
const SERVER_API_URL =
  process.env.EVOVERSE_API_URL || process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

type BackendForwardInit = {
  method: string;
  body?: unknown;
};

/**
 * Server-only relay to the backend. Identity is derived from the trusted
 * session cookie via {@link getTrustedSessionHeaders}; the browser never
 * supplies `userId`/`actorId`. In local fallback mode the session headers are
 * empty and the backend resolves its local defaults.
 */
export async function forwardToBackend(path: string, init: BackendForwardInit): Promise<Response> {
  const headers = await getTrustedSessionHeaders();
  const requestInit: RequestInit = {
    cache: "no-store",
    method: init.method,
    headers
  };
  if (init.body !== undefined) {
    headers["Content-Type"] = "application/json";
    requestInit.body = JSON.stringify(init.body);
  }
  return fetch(`${SERVER_API_URL}${path}`, requestInit);
}

/** Mirror the backend status and payload back to the calling client component. */
export async function relayBackendResponse(response: Response): Promise<Response> {
  const body = await response.text();
  return new Response(body || null, {
    status: response.status,
    headers: {
      "content-type": response.headers.get("content-type") ?? "application/json"
    }
  });
}
