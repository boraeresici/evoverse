import { NextResponse } from "next/server";
import { forwardToBackend } from "@/lib/serverApi";

export async function GET() {
  const [auditResponse, revisionsResponse] = await Promise.all([
    forwardToBackend("/admin/simulation/rules/audit?limit=20&offset=0", { method: "GET" }),
    forwardToBackend("/admin/simulation/rules/revisions?limit=20&offset=0", { method: "GET" })
  ]);

  if (!auditResponse.ok || !revisionsResponse.ok) {
    const status = !auditResponse.ok ? auditResponse.status : revisionsResponse.status;
    return NextResponse.json({ detail: "Rules history unavailable" }, { status });
  }

  const [auditPage, revisionPage] = await Promise.all([
    auditResponse.json(),
    revisionsResponse.json()
  ]);
  return NextResponse.json({ audit: auditPage.audit, revisions: revisionPage.revisions });
}
