import { NextRequest, NextResponse } from "next/server";
import { forwardToBackend, relayBackendResponse } from "@/lib/serverApi";

type RulesRollbackMutation = {
  targetRevision?: unknown;
  reason?: unknown;
};

export async function POST(request: NextRequest) {
  let payload: RulesRollbackMutation;
  try {
    payload = (await request.json()) as RulesRollbackMutation;
  } catch {
    return NextResponse.json({ detail: "Invalid request body" }, { status: 400 });
  }

  const body: Record<string, unknown> = {};
  if (payload.targetRevision !== undefined && payload.targetRevision !== null) {
    const revision = Number(payload.targetRevision);
    if (!Number.isInteger(revision) || revision < 1) {
      return NextResponse.json({ detail: "targetRevision must be a positive integer" }, { status: 400 });
    }
    body.targetRevision = revision;
  }
  if (typeof payload.reason === "string" && payload.reason.trim()) {
    body.reason = payload.reason.trim();
  }

  const backendResponse = await forwardToBackend("/admin/simulation/rules/rollback", {
    method: "POST",
    body
  });
  return relayBackendResponse(backendResponse);
}
