import { NextRequest, NextResponse } from "next/server";
import { forwardToBackend, relayBackendResponse } from "@/lib/serverApi";

type RulesChangeMutation = {
  rules?: unknown;
  reason?: unknown;
};

export async function POST(request: NextRequest) {
  let payload: RulesChangeMutation;
  try {
    payload = (await request.json()) as RulesChangeMutation;
  } catch {
    return NextResponse.json({ detail: "Invalid request body" }, { status: 400 });
  }

  if (typeof payload.rules !== "object" || payload.rules === null || Array.isArray(payload.rules)) {
    return NextResponse.json({ detail: "rules object is required" }, { status: 400 });
  }

  const body: Record<string, unknown> = { rules: payload.rules };
  if (typeof payload.reason === "string" && payload.reason.trim()) {
    body.reason = payload.reason.trim();
  }

  const backendResponse = await forwardToBackend("/admin/simulation/rules/validate", {
    method: "POST",
    body
  });
  return relayBackendResponse(backendResponse);
}
