import Link from "next/link";
import { CatalystActions } from "@/components/CatalystActions";
import { EmptyState } from "@/components/EmptyState";
import { EventList } from "@/components/EventList";
import { MicroLifeField } from "@/components/MicroLifeField";
import { ObserverFollowControl } from "@/components/ObserverFollowControl";
import { RegionInvestigationPanel } from "@/components/RegionInvestigationPanel";
import { getDynamicReport, getObserverFollows, getRegion, getSpeciesList } from "@/lib/api";

export default async function RegionPage({
  params
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const [data, follows, report, speciesData] = await Promise.all([
    getRegion(id),
    getObserverFollows(),
    getDynamicReport({ scope: "region", regionId: id, limit: 12 }),
    getSpeciesList()
  ]);

  if (!data) {
    return (
      <EmptyState
        title="Region not found"
        message="This coordinate is absent or Alpha is refreshing its current region state."
      />
    );
  }

  const initialFollowing = Boolean(
    follows?.follows.regions.some((follow) => follow.entityId === data.region.id)
  );

  return (
    <main className="page-shell">
      <section className="detail-header">
        <div>
          <p className="eyebrow">{data.region.biomeType.replaceAll("_", " ")}</p>
          <h1>{data.region.id}</h1>
          <p>{data.region.dominantSpeciesName ?? "No dominant species"}</p>
        </div>
        <div className="detail-side">
          <div className="detail-metrics">
            <span>Energy {Math.round(data.region.energyLevel * 100)}%</span>
            <span>Resources {Math.round(data.region.resourceDensity * 100)}%</span>
            <span>Stability {Math.round(data.region.stability * 100)}%</span>
          </div>
          <div className="detail-actions">
            <Link className="secondary-action" href={`/reports?scope=region&regionId=${data.region.id}`}>
              Dynamic Report
            </Link>
            <ObserverFollowControl
              entityId={data.region.id}
              entityType="region"
              initialFollowing={initialFollowing}
            />
          </div>
        </div>
      </section>

      <CatalystActions regionId={data.region.id} collapsed={data.region.collapsed} />

      <RegionInvestigationPanel
        report={report}
        populations={data.populations}
        species={speciesData?.species ?? []}
      />

      <MicroLifeField
        events={data.events}
        populations={data.populations}
        report={report}
        region={data.region}
      />

      <section className="population-list">
        {data.populations.map((population) => (
          <Link href={`/species/${population.speciesId}`} key={population.speciesId}>
            <strong>{population.speciesName}</strong>
            <span>{population.population.toLocaleString()} population</span>
            <small>{population.status}</small>
          </Link>
        ))}
      </section>

      <section className="content-band flat">
        <div className="section-heading compact-heading">
          <div>
            <p className="eyebrow">Timeline</p>
            <h2>Region Events</h2>
          </div>
        </div>
        <EventList events={data.events} />
      </section>
    </main>
  );
}
