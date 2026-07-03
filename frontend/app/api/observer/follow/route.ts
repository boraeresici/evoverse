import { NextRequest, NextResponse } from "next/server";
import { forwardToBackend, relayBackendResponse } from "@/lib/serverApi";

type FollowMutation = {
  entityId?: unknown;
  entityType?: unknown;
  follow?: unknown;
};

export async function POST(request: NextRequest) {
  let payload: FollowMutation;
  try {
    payload = (await request.json()) as FollowMutation;
  } catch {
    return NextResponse.json({ detail: "Invalid request body" }, { status: 400 });
  }

  const entityId = typeof payload.entityId === "string" ? payload.entityId.trim() : "";
  const entityType = payload.entityType === "species" ? "species" : "region";
  const follow = payload.follow !== false;
  if (!entityId) {
    return NextResponse.json({ detail: "entityId is required" }, { status: 400 });
  }

  const segment = entityType === "region" ? "regions" : "species";
  const path = `/me/follows/${segment}/${encodeURIComponent(entityId)}`;
  const backendResponse = follow
    ? await forwardToBackend(path, { method: "POST", body: {} })
    : await forwardToBackend(path, { method: "DELETE" });
  return relayBackendResponse(backendResponse);
}
