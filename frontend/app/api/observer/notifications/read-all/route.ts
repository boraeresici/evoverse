import { forwardToBackend, relayBackendResponse } from "@/lib/serverApi";

export async function POST() {
  const backendResponse = await forwardToBackend("/me/notifications/read-all", {
    method: "POST",
    body: {}
  });
  return relayBackendResponse(backendResponse);
}
