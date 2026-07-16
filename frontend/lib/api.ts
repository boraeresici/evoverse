import type {
  AdminRulesData,
  ChronicleData,
  DynamicReportData,
  DiagnosticsData,
  DynamicReportScope,
  IdentityContextData,
  LandingData,
  ObserverFollowsData,
  ObserverNotificationsData,
  RegionDetail,
  RegionSummary,
  RuleAuditPage,
  RuleRevisionPage,
  SimulationHealthData,
  SnapshotsPage,
  SpeciesDetail,
  SpeciesSummary
} from "./types";
import { getTrustedSessionHeaders } from "./authSession";
import { OBSERVER_USER_ID } from "./identity";

// Server-side reads: prefer the server-only backend origin, then the public one.
// `||` (not `??`) so an empty string falls through to the next value.
const API_URL =
  process.env.EVOVERSE_API_URL || process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
export { ADMIN_ACTOR_ID, CATALYST_USER_ID, OBSERVER_USER_ID } from "./identity";

async function request<T>(path: string): Promise<T> {
  const headers = await getTrustedSessionHeaders();
  const response = await fetch(`${API_URL}${path}`, {
    cache: "no-store",
    headers,
    next: { revalidate: 0 }
  });
  if (!response.ok) {
    throw new Error(`Evoverse API returned ${response.status} for ${path}`);
  }
  return response.json() as Promise<T>;
}

export async function getLanding(): Promise<LandingData | null> {
  try {
    return await request<LandingData>("/universes/alpha/landing");
  } catch {
    return null;
  }
}

export async function getChronicle(timeFilter = "all"): Promise<ChronicleData | null> {
  try {
    return await request<ChronicleData>(
      `/universes/alpha/chronicle?timeFilter=${encodeURIComponent(timeFilter)}`
    );
  } catch {
    return null;
  }
}

export async function getRegions(): Promise<{
  universe: ChronicleData["universe"];
  mode: string;
  regions: RegionSummary[];
} | null> {
  try {
    return await request("/universes/alpha/regions");
  } catch {
    return null;
  }
}

export async function getRegion(id: string): Promise<RegionDetail | null> {
  try {
    return await request<RegionDetail>(`/regions/${encodeURIComponent(id)}`);
  } catch {
    return null;
  }
}

export async function getSpeciesList(): Promise<{
  universe: ChronicleData["universe"];
  species: SpeciesSummary[];
} | null> {
  try {
    return await request("/species");
  } catch {
    return null;
  }
}

export async function getSpecies(id: string): Promise<SpeciesDetail | null> {
  try {
    return await request<SpeciesDetail>(`/species/${encodeURIComponent(id)}`);
  } catch {
    return null;
  }
}

export async function getObserverFollows(
  userId = OBSERVER_USER_ID
): Promise<ObserverFollowsData | null> {
  try {
    return await request<ObserverFollowsData>(
      `/me/follows?userId=${encodeURIComponent(userId)}`
    );
  } catch {
    return null;
  }
}

export async function getObserverNotifications({
  userId = OBSERVER_USER_ID,
  unreadOnly = false,
  limit = 50,
  offset = 0
}: {
  userId?: string;
  unreadOnly?: boolean;
  limit?: number;
  offset?: number;
} = {}): Promise<ObserverNotificationsData | null> {
  try {
    const params = new URLSearchParams({
      userId,
      unreadOnly: String(unreadOnly),
      limit: String(limit),
      offset: String(offset)
    });
    return await request<ObserverNotificationsData>(`/me/notifications?${params}`);
  } catch {
    return null;
  }
}

export async function getSnapshots({
  limit = 100,
  offset = 0,
  fromAge,
  toAge
}: {
  limit?: number;
  offset?: number;
  fromAge?: number | null;
  toAge?: number | null;
} = {}): Promise<SnapshotsPage | null> {
  try {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (fromAge != null) {
      params.set("fromAge", String(fromAge));
    }
    if (toAge != null) {
      params.set("toAge", String(toAge));
    }
    return await request<SnapshotsPage>(`/universes/alpha/snapshots?${params}`);
  } catch {
    return null;
  }
}

export async function getIdentityContext(): Promise<IdentityContextData | null> {
  try {
    return await request<IdentityContextData>("/me/identity");
  } catch {
    return null;
  }
}

export async function getSimulationHealth(): Promise<SimulationHealthData | null> {
  try {
    return await request<SimulationHealthData>("/admin/simulation/health");
  } catch {
    return null;
  }
}

export async function getAdminRules(): Promise<AdminRulesData | null> {
  try {
    return await request<AdminRulesData>("/admin/simulation/rules");
  } catch {
    return null;
  }
}

export async function getAdminRulesAudit({
  limit = 20,
  offset = 0
}: { limit?: number; offset?: number } = {}): Promise<RuleAuditPage | null> {
  try {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    return await request<RuleAuditPage>(`/admin/simulation/rules/audit?${params}`);
  } catch {
    return null;
  }
}

export async function getAdminRulesRevisions({
  limit = 20,
  offset = 0
}: { limit?: number; offset?: number } = {}): Promise<RuleRevisionPage | null> {
  try {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    return await request<RuleRevisionPage>(`/admin/simulation/rules/revisions?${params}`);
  } catch {
    return null;
  }
}

export async function getDynamicReport({
  scope = "universe",
  limit = 12,
  regionId,
  speciesId
}: {
  scope?: DynamicReportScope;
  limit?: number;
  regionId?: string | null;
  speciesId?: string | null;
} = {}): Promise<DynamicReportData | null> {
  try {
    const params = new URLSearchParams({
      scope,
      limit: String(limit)
    });
    if (regionId) {
      params.set("regionId", regionId);
    }
    if (speciesId) {
      params.set("speciesId", speciesId);
    }
    return await request<DynamicReportData>(`/universes/alpha/reports/dynamic?${params}`);
  } catch {
    return null;
  }
}

export async function getDiagnostics(): Promise<DiagnosticsData | null> {
  try {
    return await request<DiagnosticsData>("/universes/alpha/diagnostics");
  } catch {
    return null;
  }
}
