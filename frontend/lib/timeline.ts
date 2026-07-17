import type {
  RegionSummary,
  SnapshotAggregate,
  SnapshotRegionRow,
  SnapshotSpeciesRow,
  SpeciesSummary
} from "./types";

// Era boundaries expressed in world-age units. The literal tick -> calendar
// mapping is an open product decision (world-age conversion), so these
// thresholds are a documented placeholder chosen to keep early eras legible on
// a logarithmic axis while staying consistent with the backend's current
// "Expansion Era" for the live age range (~6k).
export type EraKey = "genesis" | "expansion" | "stabilization" | "intelligence";

export type EraBand = {
  key: EraKey;
  label: string;
  minAge: number;
  maxAge: number;
};

export const ERA_BANDS: EraBand[] = [
  { key: "genesis", label: "Genesis", minAge: 0, maxAge: 1000 },
  { key: "expansion", label: "Expansion", minAge: 1000, maxAge: 8000 },
  { key: "stabilization", label: "Stabilization", minAge: 8000, maxAge: 40000 },
  { key: "intelligence", label: "Intelligence", minAge: 40000, maxAge: Number.POSITIVE_INFINITY }
];

export function eraForAge(age: number): EraBand {
  return ERA_BANDS.find((band) => age < band.maxAge) ?? ERA_BANDS[ERA_BANDS.length - 1];
}

export type TimeZoom = {
  key: string;
  label: string;
  // Fraction of the loaded range to show, anchored at the latest frame.
  span: number;
};

/**
 * Upper bound on how many snapshot frames the backend keeps for all of world
 * history (EVOVERSE_SNAPSHOT_FRAME_BUDGET). Compaction holds the stored frame
 * count under this forever, so requesting this many is asking for the complete
 * timeline, not a page of it.
 */
export const SNAPSHOT_FRAME_BUDGET = 2000;

export const TIME_ZOOMS: TimeZoom[] = [
  { key: "recent", label: "Recent", span: 0.25 },
  { key: "mid", label: "Wider", span: 0.6 },
  { key: "full", label: "Full", span: 1 }
];

/** Position 0..1 of an age within [min,max], linear or log (early-era emphasis). */
export function axisPosition(age: number, min: number, max: number, log = false): number {
  if (max <= min) {
    return 0;
  }
  if (!log) {
    return clamp01((age - min) / (max - min));
  }
  const numerator = Math.log(age - min + 1);
  const denominator = Math.log(max - min + 1);
  return clamp01(denominator === 0 ? 0 : numerator / denominator);
}

export function ageAtPosition(position: number, min: number, max: number, log = false): number {
  const p = clamp01(position);
  if (!log) {
    return min + p * (max - min);
  }
  const denominator = Math.log(max - min + 1);
  return min + (Math.exp(p * denominator) - 1);
}

export function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * clamp01(t);
}

export function snapshotRegionToSummary(
  row: SnapshotRegionRow,
  nameById: Map<string, string>
): RegionSummary {
  return {
    id: row.regionId,
    x: row.x,
    y: row.y,
    biomeType: row.biomeType,
    energyLevel: row.energyLevel,
    resourceDensity: row.resourceDensity,
    stability: row.stability,
    lifeIndex: clamp01(Math.log10(row.populationCount + 1) / 3.6),
    chiralityEe: row.payload?.chirality_ee ?? 0,
    chiralityLocked: row.payload?.chirality_locked ?? false,
    collapsed: row.collapsed,
    dominantSpeciesId: row.dominantSpeciesId,
    dominantSpeciesName: row.dominantSpeciesId
      ? nameById.get(row.dominantSpeciesId) ?? null
      : null,
    population: row.populationCount
  };
}

export function snapshotSpeciesToSummary(row: SnapshotSpeciesRow): SpeciesSummary {
  return {
    id: row.speciesId,
    name: row.name,
    status: row.status,
    population: row.populationCount,
    originRegionId: row.originRegionId,
    emergedAtWorldAge: row.worldAge,
    generation: row.generation,
    parentSpeciesId: row.parentSpeciesId,
    chirality: row.payload?.chirality ?? 0,
    heterochiralLoad: row.payload?.heterochiral_load ?? 0,
    traits: row.traits ?? {},
    regions: [],
    forecast: {
      extinctionRisk: 0,
      dominanceProbability: 0,
      expansionPressure: 0,
      mutationVolatility: 0
    }
  };
}

export function speciesNameIndex(species: SnapshotSpeciesRow[]): Map<string, string> {
  return new Map(species.map((row) => [row.speciesId, row.name]));
}

export function stabilityOf(frame: SnapshotAggregate): number {
  const value = frame.payload?.stability_index;
  return typeof value === "number" ? value : 0;
}

export function frameSubtitle(frame: SnapshotAggregate): string {
  const era = eraForAge(frame.worldAge);
  return `Age ${frame.worldAge.toLocaleString()} · ${era.label} Era · ${frame.speciesCount.toLocaleString()} species · ${frame.populationCount.toLocaleString()} population`;
}

function clamp01(value: number): number {
  return Math.max(0, Math.min(1, value));
}
