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
  // Default to the most recent window rather than all history: the full feed runs
  // to the render cap (100 cards) and lands as a wall. Observers can widen with the
  // tabs; the active one is marked so the default filtering is never invisible.
  const timeFilter = params.timeFilter ?? "now";
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
        {[
          { key: "now", label: "Now" },
          { key: "last_24h", label: "Last 24h" },
          { key: "last_7d", label: "Last 7d" },
          { key: "all", label: "All History" }
        ].map((tab) => (
          <a
            key={tab.key}
            href={`/chronicle?timeFilter=${tab.key}`}
            className={tab.key === timeFilter ? "active" : undefined}
            aria-current={tab.key === timeFilter ? "true" : undefined}
          >
            {tab.label}
          </a>
        ))}
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
