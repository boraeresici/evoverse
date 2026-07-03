import { ChronicleFilters } from "@/components/ChronicleFilters";
import { EmptyState } from "@/components/EmptyState";
import { LiveChronicle } from "@/components/LiveChronicle";
import { StatusBand } from "@/components/StatusBand";
import { getChronicle, getRegions, getSpeciesList } from "@/lib/api";

export default async function ChroniclePage({
  searchParams
}: {
  searchParams: Promise<{
    timeFilter?: string;
    eventType?: string;
    minSeverity?: string;
    regionId?: string;
    speciesId?: string;
    query?: string;
  }>;
}) {
  const params = await searchParams;
  const timeFilter = params.timeFilter ?? "all";
  const [data, regionsData, speciesData] = await Promise.all([
    getChronicle(timeFilter),
    getRegions(),
    getSpeciesList()
  ]);

  if (!data) {
    return <EmptyState title="Chronicle is unavailable" />;
  }

  return (
    <main className="page-shell">
      <StatusBand universe={data.universe} />
      <section className="page-title">
        <p className="eyebrow">Chronicle</p>
        <h1>What Alpha Recorded</h1>
      </section>
      <div className="time-filters" aria-label="Time filters">
        <a href="/chronicle?timeFilter=now">Now</a>
        <a href="/chronicle?timeFilter=last_24h">Last 24h</a>
        <a href="/chronicle?timeFilter=last_7d">Last 7d</a>
        <a href="/chronicle?timeFilter=all">All History</a>
      </div>
      <ChronicleFilters
        events={data.events}
        regions={regionsData?.regions ?? []}
        species={speciesData?.species ?? []}
        selected={{
          eventType: params.eventType,
          minSeverity: params.minSeverity,
          regionId: params.regionId,
          speciesId: params.speciesId,
          query: params.query,
          timeFilter
        }}
      />
      <LiveChronicle
        initialEvents={data.events}
        filters={{
          eventType: params.eventType,
          minSeverity: parseSeverity(params.minSeverity),
          regionId: params.regionId,
          speciesId: params.speciesId,
          query: params.query
        }}
        timeFilter={timeFilter}
      />
    </main>
  );
}

function parseSeverity(value: string | undefined) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return undefined;
  }
  return Math.max(1, Math.min(5, Math.trunc(parsed)));
}
