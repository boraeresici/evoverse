import { NextRequest, NextResponse } from "next/server";
import { forwardToBackend, relayBackendResponse } from "@/lib/serverApi";

type CatalystActionMutation = {
  regionId?: unknown;
  actionType?: unknown;
};

export async function POST(request: NextRequest) {
  let payload: CatalystActionMutation;
  try {
    payload = (await request.json()) as CatalystActionMutation;
  } catch {
    return NextResponse.json({ detail: "Invalid request body" }, { status: 400 });
  }

  const regionId = typeof payload.regionId === "string" ? payload.regionId.trim() : "";
  const actionType = typeof payload.actionType === "string" ? payload.actionType.trim() : "";
  if (!regionId || !actionType) {
    return NextResponse.json({ detail: "regionId and actionType are required" }, { status: 400 });
  }

  const backendResponse = await forwardToBackend("/catalyst/actions", {
    method: "POST",
    body: { regionId, actionType }
  });
  return relayBackendResponse(backendResponse);
}
