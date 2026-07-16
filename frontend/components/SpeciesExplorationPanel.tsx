"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Download,
  FileJson,
  Image as ImageIcon,
  MapPin,
  Pause,
  Play,
  RadioTower,
  SkipBack,
  SkipForward
} from "lucide-react";
import { MicroLifeField } from "@/components/MicroLifeField";
import { PhylogeneticTree } from "@/components/PhylogeneticTree";
import {
  CATEGORY_META,
  categorizeTimeline,
  summarizeCategories,
  type CategorizedEvent,
  type EventCategory
} from "@/lib/speciesEvents";
import { CARD_HEIGHT, CARD_WIDTH, buildSpeciesCardSvg } from "@/lib/speciesCard";
import type { DynamicReportData, RegionDetail, SpeciesDetail, SpeciesSummary } from "@/lib/types";

type SpeciesExplorationPanelProps = {
  data: SpeciesDetail;
  allSpecies: SpeciesSummary[];
  report: DynamicReportData | null;
};

const PLAYBACK_INTERVAL_MS = 1600;

export function SpeciesExplorationPanel({
  data,
  allSpecies,
  report
}: SpeciesExplorationPanelProps) {
  const extinctLineage = data.species.status === "extinct";

  const timeline = useMemo(() => {
    const events = data.events
      .filter((event) => event.worldAge >= data.species.emergedAtWorldAge)
      .sort((a, b) => a.worldAge - b.worldAge);
    return categorizeTimeline(events, { extinctLineage });
  }, [data.events, data.species.emergedAtWorldAge, extinctLineage]);

  const [selectedIndex, setSelectedIndex] = useState(0);
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    setSelectedIndex(0);
    setPlaying(false);
  }, [data.species.id]);

  useEffect(() => {
    if (!playing || timeline.length === 0) {
      return;
    }
    const timer = window.setInterval(() => {
      setSelectedIndex((index) => {
        if (index >= timeline.length - 1) {
          setPlaying(false);
          return index;
        }
        return index + 1;
      });
    }, PLAYBACK_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [playing, timeline.length]);

  const selected = timeline[selectedIndex] ?? timeline[0] ?? null;
  const speciesProjection = useMemo(() => speciesReplayProjection(data), [data]);
  const categorySummary = useMemo(() => summarizeCategories(timeline), [timeline]);

  const nowAge = useMemo(() => {
    const emergenceMax = allSpecies.reduce(
      (max, item) => Math.max(max, item.emergedAtWorldAge),
      data.species.emergedAtWorldAge
    );
    return Math.max(report?.current?.worldAge ?? 0, emergenceMax);
  }, [report, allSpecies, data.species.emergedAtWorldAge]);

  const majorMutationAges = useMemo(
    () =>
      timeline
        .filter((item) => item.category === "major_mutation")
        .map((item) => item.event.worldAge),
    [timeline]
  );

  const step = useCallback(
    (delta: number) => {
      setPlaying(false);
      setSelectedIndex((index) => Math.max(0, Math.min(timeline.length - 1, index + delta)));
    },
    [timeline.length]
  );

  return (
    <section className="species-exploration">
      <div className="section-heading compact-heading">
        <div>
          <p className="eyebrow">Evolution</p>
          <h2>Lineage Investigation</h2>
        </div>
        <ShareableSpeciesCard data={data} />
      </div>

      <div className="evolution-stack">
        <article className="evolution-tree">
          <header className="evolution-tree-head">
            <h3>Phylogenetic Tree</h3>
            <span>Generation {data.species.generation}</span>
          </header>
          <PhylogeneticTree
            current={data.species}
            allSpecies={allSpecies}
            nowAge={nowAge}
            majorMutationAges={majorMutationAges}
          />
        </article>

        <article className="species-replay">
          <header>
            <div>
              <p className="eyebrow">Replay Lite</p>
              <h3>Emergence to Now</h3>
            </div>
            <div className="replay-actions">
              <button aria-label="Previous event" disabled={!timeline.length} onClick={() => step(-1)} type="button">
                <SkipBack size={16} aria-hidden="true" />
              </button>
              <button
                aria-label={playing ? "Pause replay" : "Play replay"}
                className="replay-play"
                disabled={timeline.length < 2}
                onClick={() => setPlaying((value) => !value)}
                type="button"
              >
                {playing ? <Pause size={16} aria-hidden="true" /> : <Play size={16} aria-hidden="true" />}
              </button>
              <button aria-label="Next event" disabled={!timeline.length} onClick={() => step(1)} type="button">
                <SkipForward size={16} aria-hidden="true" />
              </button>
            </div>
          </header>

          <ReplayChart
            events={timeline}
            report={report}
            selectedId={selected?.event.id ?? null}
            onSelect={(id) => {
              setPlaying(false);
              const index = timeline.findIndex((item) => item.event.id === id);
              if (index >= 0) {
                setSelectedIndex(index);
              }
            }}
          />

          {timeline.length ? (
            <div className="replay-progress" aria-hidden="true">
              <span style={{ width: `${((selectedIndex + 1) / timeline.length) * 100}%` }} />
            </div>
          ) : null}

          <CategoryLegend summary={categorySummary} />

          {selected ? (
            <div className={`replay-event tone-${selected.tone}`}>
              <span className={`replay-event-badge tone-${selected.tone}`}>{selected.label}</span>
              <span className="replay-event-body">
                <strong>{selected.event.title}</strong>
                <small>
                  Age {selected.event.worldAge.toLocaleString()}
                  {selected.event.regionName || selected.event.regionId ? (
                    <>
                      {" · "}
                      <MapPin size={11} aria-hidden="true" />
                      {selected.event.regionName ?? selected.event.regionId}
                    </>
                  ) : null}
                  {` · ${selectedIndex + 1}/${timeline.length}`}
                </small>
                <em>{selected.event.summary}</em>
              </span>
            </div>
          ) : (
            <div className="replay-event tone-neutral">
              <RadioTower size={17} aria-hidden="true" />
              <span className="replay-event-body">
                <strong>No replay event yet</strong>
                <small>Alpha has not recorded a lineage event in this window.</small>
              </span>
            </div>
          )}

          <MicroLifeField
            compact
            events={timeline.map((item) => item.event)}
            eyebrow="Species Micro Replay"
            populations={speciesProjection.populations}
            region={speciesProjection.region}
            report={report}
            title="Distribution Field"
          />
        </article>
      </div>
    </section>
  );
}

function ReplayChart({
  events,
  report,
  selectedId,
  onSelect
}: {
  events: CategorizedEvent[];
  report: DynamicReportData | null;
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const chart = chartGeometry(report?.series ?? [], "populationCount");
  const markers = markerGeometry(events, chart.startAge, chart.endAge);

  if (!report || !report.series.length) {
    return <p className="species-chart-empty">Population chart is waiting for snapshot coverage.</p>;
  }

  return (
    <svg
      className="species-population-chart"
      role="img"
      aria-label="Species population chart with event markers"
      viewBox="0 0 620 220"
    >
      <path className="chart-grid-line" d="M0 36 H620" />
      <path className="chart-grid-line" d="M0 110 H620" />
      <path className="chart-grid-line" d="M0 184 H620" />
      <polyline className="chart-line" fill="none" points={chart.points} />
      {chart.dots.map((dot) => (
        <circle cx={dot.x} cy={dot.y} key={`${dot.x}-${dot.y}`} r="4.5" />
      ))}
      {markers.map((marker) => {
        const active = marker.id === selectedId;
        return (
          <g
            className={`event-marker tone-${marker.tone}${active ? " active" : ""}`}
            key={marker.id}
            role="button"
            tabIndex={0}
            aria-label={`${marker.label} at age ${marker.worldAge}`}
            onClick={() => onSelect(marker.id)}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                onSelect(marker.id);
              }
            }}
          >
            <rect className="marker-hit" x={marker.x - 8} y="20" width="16" height="180" />
            <line x1={marker.x} x2={marker.x} y1="28" y2="194" />
            <circle cx={marker.x} cy="28" r={marker.important ? 6 : 4} />
          </g>
        );
      })}
    </svg>
  );
}

function CategoryLegend({
  summary
}: {
  summary: Array<{ category: EventCategory; count: number }>;
}) {
  if (!summary.length) {
    return null;
  }
  return (
    <div className="replay-legend" aria-label="Event category legend">
      {summary.map(({ category, count }) => {
        const meta = CATEGORY_META[category];
        return (
          <span className={`legend-chip tone-${meta.tone}`} key={category}>
            <i aria-hidden="true" />
            {meta.label}
            <strong>{count}</strong>
          </span>
        );
      })}
    </div>
  );
}

function ShareableSpeciesCard({ data }: { data: SpeciesDetail }) {
  const [busy, setBusy] = useState(false);
  const svgMarkup = useMemo(() => buildSpeciesCardSvg(data), [data]);
  const cardRef = useRef<HTMLDivElement | null>(null);

  const downloadPng = useCallback(async () => {
    setBusy(true);
    try {
      const blob = new Blob([svgMarkup], { type: "image/svg+xml;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      await new Promise<void>((resolve, reject) => {
        const image = new window.Image();
        image.onload = () => {
          const scale = 2;
          const canvas = document.createElement("canvas");
          canvas.width = CARD_WIDTH * scale;
          canvas.height = CARD_HEIGHT * scale;
          const ctx = canvas.getContext("2d");
          if (!ctx) {
            reject(new Error("Canvas unavailable"));
            return;
          }
          ctx.scale(scale, scale);
          ctx.drawImage(image, 0, 0);
          URL.revokeObjectURL(url);
          canvas.toBlob((pngBlob) => {
            if (!pngBlob) {
              reject(new Error("PNG encode failed"));
              return;
            }
            triggerDownload(URL.createObjectURL(pngBlob), `${data.species.id}-card.png`, true);
            resolve();
          }, "image/png");
        };
        image.onerror = () => reject(new Error("SVG load failed"));
        image.src = url;
      });
    } catch {
      /* PNG export is best-effort; the SVG preview and JSON export remain */
    } finally {
      setBusy(false);
    }
  }, [svgMarkup, data.species.id]);

  const downloadJson = useCallback(() => {
    const payload = JSON.stringify(
      {
        species: data.species,
        children: data.children,
        eventCount: data.events.length
      },
      null,
      2
    );
    const blob = new Blob([payload], { type: "application/json" });
    triggerDownload(URL.createObjectURL(blob), `${data.species.id}-species-card.json`, true);
  }, [data]);

  return (
    <div className="species-card-share">
      <div
        className="species-card-preview"
        ref={cardRef}
        aria-label={`${data.species.name} shareable card preview`}
        dangerouslySetInnerHTML={{ __html: svgMarkup }}
      />
      <div className="species-card-actions">
        <button className="secondary-action" disabled={busy} onClick={() => void downloadPng()} type="button">
          {busy ? <Download size={16} aria-hidden="true" /> : <ImageIcon size={16} aria-hidden="true" />}
          {busy ? "Rendering…" : "Download PNG"}
        </button>
        <button className="secondary-action ghost" onClick={downloadJson} type="button">
          <FileJson size={16} aria-hidden="true" />
          Export JSON
        </button>
      </div>
    </div>
  );
}

function triggerDownload(url: string, filename: string, revoke: boolean) {
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  if (revoke) {
    URL.revokeObjectURL(url);
  }
}

function speciesReplayProjection(data: SpeciesDetail): {
  region: RegionDetail["region"];
  populations: RegionDetail["populations"];
} {
  const traits = data.species.traits;
  const efficiency = Number(traits.efficiency ?? 0.5);
  const adaptation = Number(traits.adaptation ?? 0.5);
  const cooperation = Number(traits.cooperation ?? 0.5);
  const mobility = Number(traits.mobility ?? 0.5);
  const resilience = Number(traits.resilience ?? 0.5);
  const extinctionRisk = data.species.forecast.extinctionRisk;
  const expansion = data.species.forecast.expansionPressure;

  return {
    region: {
      id: data.species.originRegionId,
      x: 0,
      y: 0,
      biomeType: "species_distribution",
      energyLevel: clamp01(efficiency * 0.5 + adaptation * 0.25 + cooperation * 0.25),
      resourceDensity: clamp01(adaptation * 0.35 + mobility * 0.25 + expansion * 0.4),
      stability: clamp01(resilience * 0.45 + cooperation * 0.2 + (1 - extinctionRisk) * 0.35),
      lifeIndex: clamp01(Math.log10(data.species.population + 1) / 5.4),
      // Synthetic distribution field, not a real region: it stands for the lineage,
      // so it carries the lineage's own hand rather than any region's.
      chiralityEe: data.species.chirality,
      chiralityLocked: data.species.chirality !== 0,
      collapsed: data.species.status === "extinct",
      dominantSpeciesId: data.species.id,
      dominantSpeciesName: data.species.name,
      population: data.species.population
    },
    populations: data.species.regions.length
      ? data.species.regions.map((region) => ({
          speciesId: data.species.id,
          speciesName: data.species.name,
          status: data.species.status,
          population: region.population,
          growthRate: clamp01(expansion) * 0.08 - clamp01(extinctionRisk) * 0.05,
          migrationPressure: clamp01(mobility * region.share)
        }))
      : [
          {
            speciesId: data.species.id,
            speciesName: data.species.name,
            status: data.species.status,
            population: data.species.population,
            growthRate: clamp01(expansion) * 0.08,
            migrationPressure: clamp01(mobility)
          }
        ]
  };
}

function clamp01(value: number) {
  return Math.max(0, Math.min(1, value));
}

function chartGeometry(series: DynamicReportData["series"], metricKey: string) {
  const values = series.map((point) => Number(point.metrics[metricKey] ?? 0));
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const width = 620;
  const height = 156;
  const top = 34;
  const dots = series.map((point, index) => {
    const value = Number(point.metrics[metricKey] ?? 0);
    const x = series.length === 1 ? width / 2 : (index / (series.length - 1)) * width;
    const y = top + height - ((value - min) / range) * height;
    return {
      x: Math.round(x * 100) / 100,
      y: Math.round(y * 100) / 100
    };
  });
  return {
    points: dots.map((dot) => `${dot.x},${dot.y}`).join(" "),
    dots,
    startAge: series[0]?.worldAge ?? 0,
    endAge: series[series.length - 1]?.worldAge ?? 0
  };
}

function markerGeometry(events: CategorizedEvent[], startAge: number, endAge: number) {
  const width = 620;
  const range = endAge - startAge || 1;
  return events.map((item) => ({
    id: item.event.id,
    x: Math.max(0, Math.min(width, ((item.event.worldAge - startAge) / range) * width)),
    important: item.important,
    tone: item.tone,
    label: item.label,
    worldAge: item.event.worldAge
  }));
}
