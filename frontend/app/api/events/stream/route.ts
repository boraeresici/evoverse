import { NextRequest } from "next/server";
import { forwardToBackend } from "@/lib/serverApi";

// Long-lived SSE proxy: the browser connects to this same-origin route, and we
// pipe the backend event stream through. Keeps the backend off the browser (no
// CORS, no public API host), consistent with the other BFF routes.
export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(request: NextRequest) {
  const lastEventId = request.nextUrl.searchParams.get("lastEventId");
  const query = lastEventId ? `?lastEventId=${encodeURIComponent(lastEventId)}` : "";

  const upstream = await forwardToBackend(`/universes/alpha/events/stream${query}`, {
    method: "GET"
  });

  if (!upstream.ok || !upstream.body) {
    return new Response("event: stream_status\ndata: unavailable\n\n", {
      status: upstream.status || 502,
      headers: { "content-type": "text/event-stream" }
    });
  }

  return new Response(upstream.body, {
    status: 200,
    headers: {
      "content-type": "text/event-stream; charset=utf-8",
      "cache-control": "no-cache, no-transform",
      connection: "keep-alive",
      "x-accel-buffering": "no"
    }
  });
}
