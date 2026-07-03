"use client";

import Link from "next/link";
import type { CSSProperties } from "react";
import { useMemo, useState } from "react";
import { Activity, Dna, Gauge, Search, Sparkles, Zap } from "lucide-react";
import { hexLayout, eventWaveRings } from "@/lib/hexMap";
import { lifeTextureVars, speciesDiversityByRegion } from "@/lib/lifeTexture";
import type { ChronicleEvent, RegionSummary, SpeciesSummary } from "@/lib/types";

type MapMode = "life" | "energy" | "mutation" | "stability";

type UniverseExplorerProps = {
  regions: RegionSummary[];
  species: SpeciesSummary[];
  events: ChronicleEvent[];
};

const mapModes: Array<{
  id: MapMode;
  label: string;
  icon: typeof Activity;
}> = [
  { id: "life", label: "Life", icon: Dna },
  { id: "energy", label: "Energy", icon: Zap },
  { id: "mutation", label: "Mutation", icon: Sparkles },
  { id: "stability", label: "Stability", icon: Gauge }
];

export function UniverseExplorer({ regions, species, events }: UniverseExplorerProps) {
  const [mode, setMode] = useState<MapMode>("life");
  const [query, setQuery] = useState("");
  const eventByRegion = useMemo(() => latestEventByRegion(events), [events]);
  const mutationSignalByRegion = useMemo(() => mutationSignals(events), [events]);
  const diversityByRegion = useMemo(() => speciesDiversityByRegion(species), [species]);
  const matchedRegionIds = useMemo(
    () => matchingRegionIds(regions, species, query),
    [query, regions, species]
  );
  const focusedRegions = useMemo(
    () => focusRegions(regions, matchedRegionIds, query),
    [matchedRegionIds, query, regions]
  );
  const layout = useMemo(() => hexLayout(regions), [regions]);
  const waveRings = useMemo(() => eventWaveRings(regions, events), [regions, events]);
  const avgStability = useMemo(
    () =>
      regions.length
        ? regions.reduce((sum, region) => sum + region.stability, 0) / regions.length
        : 0.5,
    [regions]
  );
  // Calmer (slower) breathing when Alpha is globally stable.
  const breathDuration = (3.5 + avgStability * 3.5).toFixed(2);
  const hasQuery = query.trim().length > 0;

  return (
    <section className="universe-explorer">
      <div className="map-controls">
        <div className="mode-tabs" aria-label="Universe map mode">
          {mapModes.map((item) => {
            const Icon = item.icon;
            return (
              <button
                aria-pressed={mode === item.id}
                className={mode === item.id ? "mode-button active" : "mode-button"}
                key={item.id}
                onClick={() => setMode(item.id)}
                type="button"
              >
                <Icon size={16} aria-hidden="true" />
                {item.label}
              </button>
            );
          })}
        </div>
        <label className="region-search">
          <Search size={16} aria-hidden="true" />
          <input
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search region, biome, or species"
            type="search"
            value={query}
          />
        </label>
      </div>

      <div className="map-shell investigation-map">
        <div className="map-toolbar">
          <span>{modeLabel(mode)}</span>
          <span>{hasQuery ? `${matchedRegionIds.size} matches` : `${regions.length} regions`}</span>
          <span>{events.length} recent signals</span>
        </div>
        <div
          className="universe-hexmap"
          aria-label="Alpha investigation map"
          style={
            {
              aspectRatio: String(layout.aspectRatio),
              "--breath-duration": `${breathDuration}s`
            } as CSSProperties
          }
        >
          {layout.cells.map(({ region, leftPct, topPct, widthPct, heightPct }) => {
            const latestEvent = eventByRegion.get(region.id);
            const mutationSignal = mutationSignalByRegion.get(region.id) ?? 0;
            const eventSignal = latestEvent ? latestEvent.severity / 5 : mutationSignal;
            const matched = matchedRegionIds.has(region.id);
            const ring = waveRings.get(region.id);
            const cellClasses = [
              "region-cell",
              latestEvent ? "has-event" : "",
              hasQuery && !matched ? "dimmed" : ""
            ]
              .filter(Boolean)
              .join(" ");
            const hexClasses = [
              "region-hex",
              region.collapsed ? "collapsed" : "",
              region.lifeIndex > 0.12 ? "alive" : ""
            ]
              .filter(Boolean)
              .join(" ");

            return (
              <Link
                aria-label={`${region.id}, ${region.dominantSpeciesName ?? "no dominant species"}`}
                className={cellClasses}
                data-wave={ring === undefined ? undefined : ring}
                href={`/regions/${region.id}`}
                key={region.id}
                style={{
                  left: `${leftPct}%`,
                  top: `${topPct}%`,
                  width: `${widthPct}%`,
                  height: `${heightPct}%`
                }}
              >
                <span
                  className={hexClasses}
                  data-mode={mode}
                  style={
                    {
                      "--life": region.lifeIndex,
                      "--energy": region.energyLevel,
                      "--stability": region.stability,
                      "--risk": 1 - region.stability,
                      "--mutation": mutationSignal,
                      ...lifeTextureVars(region, {
                        diversity: diversityByRegion.get(region.id) ?? 0,
                        eventSignal
                      })
                    } as CSSProperties
                  }
                >
                  <span className="region-life-texture" aria-hidden="true" />
                </span>
                {latestEvent ? (
                  <span
                    className={`region-event-dot severity-${latestEvent.severity}`}
                    title={latestEvent.eventLabel}
                  />
                ) : null}
                <span className="region-tooltip">
                  <strong>{region.id}</strong>
                  <small>{region.biomeType.replaceAll("_", " ")}</small>
                  <small>{region.dominantSpeciesName ?? "No dominant species"}</small>
                  <small>{region.population.toLocaleString()} aggregate population</small>
                  <em>Zoom into life field</em>
                  {latestEvent ? <em>{latestEvent.eventLabel}</em> : null}
                </span>
              </Link>
            );
          })}
        </div>
      </div>

      <section className="investigation-results" aria-label="Focused regions">
        {focusedRegions.map((region) => (
          <article className="investigation-region-row" key={region.id}>
            <div>
              <strong>{region.id}</strong>
              <span>{region.dominantSpeciesName ?? "Unclaimed"}</span>
              <small>
                {region.biomeType.replaceAll("_", " ")} /{" "}
                {region.population.toLocaleString()} population
              </small>
            </div>
            <div className="investigation-links">
              <Link href={`/regions/${region.id}`}>Open</Link>
              <Link href={`/reports?scope=region&regionId=${region.id}`}>Report</Link>
            </div>
          </article>
        ))}
      </section>
    </section>
  );
}

function latestEventByRegion(events: ChronicleEvent[]) {
  const map = new Map<string, ChronicleEvent>();
  for (const event of events) {
    if (!event.regionId) {
      continue;
    }
    const current = map.get(event.regionId);
    if (!current || event.worldAge >= current.worldAge) {
      map.set(event.regionId, event);
    }
  }
  return map;
}

function mutationSignals(events: ChronicleEvent[]) {
  const map = new Map<string, number>();
  for (const event of events) {
    if (!event.regionId) {
      continue;
    }
    const mutationWeight =
      event.eventType.includes("mutation") || event.eventType.includes("species") ? 0.28 : 0.08;
    map.set(event.regionId, Math.min(1, (map.get(event.regionId) ?? 0) + mutationWeight));
  }
  return map;
}

function matchingRegionIds(
  regions: RegionSummary[],
  species: SpeciesSummary[],
  query: string
) {
  const normalized = query.trim().toLowerCase();
  if (!normalized) {
    return new Set(regions.map((region) => region.id));
  }

  const speciesRegionIds = new Set<string>();
  for (const item of species) {
    const speciesMatch = [item.id, item.name, item.status, item.originRegionId]
      .join(" ")
      .toLowerCase()
      .includes(normalized);
    if (!speciesMatch) {
      continue;
    }
    speciesRegionIds.add(item.originRegionId);
    for (const region of item.regions) {
      speciesRegionIds.add(region.regionId);
    }
  }

  return new Set(
    regions
      .filter((region) =>
        [
          region.id,
          region.biomeType,
          region.dominantSpeciesName ?? "",
          region.dominantSpeciesId ?? ""
        ]
          .join(" ")
          .toLowerCase()
          .includes(normalized) || speciesRegionIds.has(region.id)
      )
      .map((region) => region.id)
  );
}

function focusRegions(regions: RegionSummary[], matchedIds: Set<string>, query: string) {
  const pool = query.trim()
    ? regions.filter((region) => matchedIds.has(region.id))
    : [...regions].sort((a, b) => b.population - a.population);
  return pool.slice(0, 8);
}

function modeLabel(mode: MapMode) {
  return `${mode.charAt(0).toUpperCase()}${mode.slice(1)} mode`;
}
