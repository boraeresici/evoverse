import { NextRequest, NextResponse } from "next/server";
import { forwardToBackend, relayBackendResponse } from "@/lib/serverApi";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ tick: string }> }
) {
  const { tick } = await params;
  const parsed = Number(tick);
  if (!Number.isInteger(parsed) || parsed < 0) {
    return NextResponse.json({ detail: "tick must be a non-negative integer" }, { status: 400 });
  }

  const backendResponse = await forwardToBackend(
    `/universes/alpha/snapshots/${parsed}/details`,
    { method: "GET" }
  );
  return relayBackendResponse(backendResponse);
}
