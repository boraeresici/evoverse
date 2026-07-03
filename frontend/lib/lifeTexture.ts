import type { RegionSummary, SpeciesSummary } from "./types";

type LifeTextureOptions = {
  diversity?: number;
  eventSignal?: number;
};

type LifeTextureVars = Record<`--${string}`, string | number>;

export function lifeTextureVars(
  region: RegionSummary,
  { diversity = 0, eventSignal = 0 }: LifeTextureOptions = {}
): LifeTextureVars {
  const populationDensity = clamp(Math.log10(region.population + 1) / 5.4);
  const density = clamp(0.12 + region.lifeIndex * 0.52 + populationDensity * 0.26);
  const pulse = clamp(eventSignal * 0.42 + (1 - region.stability) * 0.2 + region.energyLevel * 0.12);
  const hue = hashHue(region.dominantSpeciesId ?? region.dominantSpeciesName ?? region.id);

  return {
    "--texture-density": density.toFixed(3),
    "--texture-diversity": clamp(diversity).toFixed(3),
    "--texture-pulse": pulse.toFixed(3),
    "--texture-hue": hue
  };
}

export function speciesDiversityByRegion(species: SpeciesSummary[]) {
  const counts = new Map<string, number>();

  for (const item of species) {
    for (const region of item.regions) {
      if (region.population <= 0) {
        continue;
      }
      counts.set(region.regionId, (counts.get(region.regionId) ?? 0) + 1);
    }
  }

  const normalized = new Map<string, number>();
  for (const [regionId, count] of counts) {
    normalized.set(regionId, clamp(count / 5));
  }
  return normalized;
}

function hashHue(value: string) {
  let hash = 0;
  for (let index = 0; index < value.length; index += 1) {
    hash = (hash * 31 + value.charCodeAt(index)) % 360;
  }
  return hash;
}

function clamp(value: number) {
  return Math.max(0, Math.min(1, value));
}
