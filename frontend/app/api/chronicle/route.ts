import { NextRequest } from "next/server";
import { forwardToBackend, relayBackendResponse } from "@/lib/serverApi";

// Same-origin proxy for the chronicle polling fallback used by LiveChronicle.
export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const timeFilter = request.nextUrl.searchParams.get("timeFilter") ?? "all";
  const upstream = await forwardToBackend(
    `/universes/alpha/chronicle?timeFilter=${encodeURIComponent(timeFilter)}`,
    { method: "GET" }
  );
  return relayBackendResponse(upstream);
}
