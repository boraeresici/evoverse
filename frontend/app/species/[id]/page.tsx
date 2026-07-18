import Link from "next/link";
import { GitBranch, Star } from "lucide-react";
import { EmptyState } from "@/components/EmptyState";
import { EventTimeline } from "@/components/EventTimeline";
import { ForecastPanel } from "@/components/ForecastPanel";
import { ObserverFollowControl } from "@/components/ObserverFollowControl";
import { PageHelp } from "@/components/PageHelp";
import { SpeciesExplorationPanel } from "@/components/SpeciesExplorationPanel";

const SPECIES_HELP = [
  {
    heading: "Traits & forecast",
    body: "Trait bars show the species' current makeup. The forecast gauges (extinction, dominance, expansion, mutation) and the population fan chart project a likely trajectory — a visualization from forecast signals, not a backend prediction."
  },
  {
    heading: "Phylogenetic tree",
    body: "A time-axis tree: x is the world age a species emerged, y is its lineage. Branches show radiation; extinct branches fade and end with an ✕. Click any node to recenter on that species."
  },
  {
    heading: "Replay & markers",
    body: "The population chart marks events by category (emergence, mutation, extinction…). Play steps through the lineage timeline; the Distribution Field animates a sampled micro-view."
  },
  {
    heading: "Follow & share",
    body: "Follow the species to collect its activity in your notifications digest, or export a shareable PNG species card."
  }
];
import {
  getDynamicReport,
  getObserverFollows,
  getRegions,
  getSpecies,
  getSpeciesList
} from "@/lib/api";

export default async function SpeciesPage({
  params
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  // The origin region id only arrives with the species, but fetching the region
  // list alongside keeps this one round trip instead of two — the page already
  // pulls the full species list the same way.
  const [data, follows, report, speciesList, regions] = await Promise.all([
    getSpecies(id),
    getObserverFollows(),
    getDynamicReport({ scope: "species", speciesId: id, limit: 18 }),
    getSpeciesList(),
    getRegions()
  ]);

  if (!data) {
    return (
      <EmptyState
        title="Species not found"
        message="This lineage is absent or Alpha is refreshing its current species state."
      />
    );
  }

  const initialFollowing = Boolean(
    follows?.follows.species.some((follow) => follow.entityId === data.species.id)
  );

  return (
    <main className="page-shell">
      <section className="detail-header species-header">
        <div>
          <p className="eyebrow">Generation {data.species.generation}</p>
          <h1>{data.species.name}</h1>
          <p>
            {data.species.status} / {data.species.population.toLocaleString()} population
          </p>
        </div>
        <div className="detail-actions">
          <Link className="secondary-action" href={`/regions/${data.species.originRegionId}`}>
            <GitBranch size={17} aria-hidden="true" />
            Origin Region
          </Link>
          <ObserverFollowControl
            entityId={data.species.id}
            entityType="species"
            initialFollowing={initialFollowing}
          />
        </div>
      </section>

      <PageHelp points={SPECIES_HELP} />

      <section className="trait-grid">
        {Object.entries(data.species.traits).map(([trait, value]) => (
          <div className="trait-row" key={trait}>
            <span>{trait}</span>
            <div className="trait-track">
              <i style={{ width: `${Math.round(value * 100)}%` }} />
            </div>
            <strong>{Math.round(value * 100)}%</strong>
          </div>
        ))}
      </section>

      <ForecastPanel species={data.species} report={report} />

      <SpeciesExplorationPanel
        data={data}
        allSpecies={speciesList?.species ?? []}
        report={report}
        originRegion={
          regions?.regions.find((region) => region.id === data.species.originRegionId) ?? null
        }
      />

      <section className="population-list">
        {data.species.regions.map((region) => (
          <Link href={`/regions/${region.regionId}`} key={region.regionId}>
            <strong>{region.regionId}</strong>
            <span>{region.population.toLocaleString()} population</span>
            <small>{Math.round(region.share * 100)}% share</small>
          </Link>
        ))}
      </section>

      {data.children.length ? (
        <section className="species-children">
          {data.children.map((child) => (
            <Link href={`/species/${child.id}`} key={child.id}>
              <Star size={16} aria-hidden="true" />
              {child.name}
            </Link>
          ))}
        </section>
      ) : null}

      <section className="content-band flat">
        <div className="section-heading compact-heading">
          <div>
            <p className="eyebrow">Timeline</p>
            <h2>Species Events</h2>
          </div>
        </div>
        <EventTimeline events={data.events} />
      </section>
    </main>
  );
}
