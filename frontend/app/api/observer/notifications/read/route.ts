import { NextRequest, NextResponse } from "next/server";
import { forwardToBackend, relayBackendResponse } from "@/lib/serverApi";

type NotificationReadMutation = {
  notificationId?: unknown;
};

export async function POST(request: NextRequest) {
  let payload: NotificationReadMutation;
  try {
    payload = (await request.json()) as NotificationReadMutation;
  } catch {
    return NextResponse.json({ detail: "Invalid request body" }, { status: 400 });
  }

  const notificationId =
    typeof payload.notificationId === "string" ? payload.notificationId.trim() : "";
  if (!notificationId) {
    return NextResponse.json({ detail: "notificationId is required" }, { status: 400 });
  }

  const backendResponse = await forwardToBackend(
    `/me/notifications/${encodeURIComponent(notificationId)}/read`,
    { method: "POST", body: {} }
  );
  return relayBackendResponse(backendResponse);
}
