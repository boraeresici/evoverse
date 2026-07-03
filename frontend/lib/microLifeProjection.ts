import type { ChronicleEvent, RegionDetail } from "./types";

export type MicroLifeMode = "life" | "species" | "resources" | "events";

export type MicroLifeAgent = {
  id: string;
  speciesId: string;
  speciesName: string;
  x: number;
  y: number;
  radius: number;
  hue: number;
  phase: number;
  driftX: number;
  driftY: number;
  share: number;
  growthRate: number;
  migrationPressure: number;
};

export type MicroLifeResourceNode = {
  id: string;
  x: number;
  y: number;
  radius: number;
  strength: number;
  phase: number;
};

export type MicroLifeProjection = {
  agents: MicroLifeAgent[];
  resources: MicroLifeResourceNode[];
  signals: {
    mutation: number;
    migration: number;
    collapse: number;
    catalyst: number;
    recovery: number;
  };
  summary: {
    agentCount: number;
    totalPopulation: number;
    speciesCount: number;
    latestEventLabel: string | null;
  };
};

type MicroLifeProjectionInput = {
  region: RegionDetail["region"];
  populations: RegionDetail["populations"];
  events: ChronicleEvent[];
  projectionContext?: number | string | null;
};

export function buildMicroLifeProjection({
  region,
  populations,
  events,
  projectionContext
}: MicroLifeProjectionInput): MicroLifeProjection {
  const sortedPopulations = [...populations].sort((a, b) => b.population - a.population);
  const totalPopulation = sortedPopulations.reduce((total, item) => total + item.population, 0);
  const speciesCount = new Set(sortedPopulations.map((item) => item.speciesId)).size;
  const latestEvent = events[0] ?? null;
  const seed = hashString(
    [
      region.id,
      region.population,
      region.energyLevel.toFixed(3),
      region.resourceDensity.toFixed(3),
      region.stability.toFixed(3),
      projectionContext ?? "current",
      latestEvent?.id ?? "steady"
    ].join(":")
  );
  const random = seededRandom(seed);
  const populationDensity = clamp(Math.log10(totalPopulation + 1) / 5.4);
  const fieldEnergy = clamp(region.energyLevel * 0.4 + region.resourceDensity * 0.34 + region.lifeIndex * 0.26);
  const baseAgents = Math.round(96 + populationDensity * 92 + fieldEnergy * 68);
  const agentCount = region.collapsed ? Math.max(52, Math.round(baseAgents * 0.42)) : Math.min(256, baseAgents);
  const signals = eventSignals(events, region.collapsed);

  const agents: MicroLifeAgent[] = [];
  const populationPool = sortedPopulations.length
    ? sortedPopulations
    : [
        {
          speciesId: "unclaimed",
          speciesName: "Unclaimed signal",
          status: "emerging",
          population: Math.max(1, region.population),
          growthRate: 0,
          migrationPressure: 0
        }
      ];

  const dominantHue = hashHue(region.dominantSpeciesId ?? region.dominantSpeciesName ?? region.id);

  for (const population of populationPool) {
    const share = totalPopulation ? population.population / totalPopulation : 1 / populationPool.length;
    const speciesAgents = Math.max(3, Math.round(agentCount * share));
    const hue = population.speciesId === region.dominantSpeciesId
      ? dominantHue
      : hashHue(population.speciesId);
    const clusterAngle = random() * Math.PI * 2;
    const clusterRadius = 0.08 + random() * 0.22;
    const centerX = clamp(0.5 + Math.cos(clusterAngle) * clusterRadius);
    const centerY = clamp(0.5 + Math.sin(clusterAngle) * clusterRadius);

    for (let index = 0; index < speciesAgents && agents.length < agentCount; index += 1) {
      const localAngle = random() * Math.PI * 2;
      const localRadius = Math.sqrt(random()) * (0.16 + (1 - share) * 0.18);
      const radius = 1.7 + share * 2.8 + random() * 1.8;
      agents.push({
        id: `${population.speciesId}-${index}`,
        speciesId: population.speciesId,
        speciesName: population.speciesName,
        x: clamp(centerX + Math.cos(localAngle) * localRadius),
        y: clamp(centerY + Math.sin(localAngle) * localRadius),
        radius,
        hue,
        phase: random() * Math.PI * 2,
        driftX: (random() - 0.5) * (0.018 + population.migrationPressure * 0.1),
        driftY: (random() - 0.5) * (0.018 + population.migrationPressure * 0.1),
        share,
        growthRate: population.growthRate,
        migrationPressure: population.migrationPressure
      });
    }
  }

  while (agents.length < agentCount) {
    const hue = hashHue(region.id);
    agents.push({
      id: `ambient-${agents.length}`,
      speciesId: "ambient",
      speciesName: "Ambient field",
      x: random(),
      y: random(),
      radius: 1.6 + random() * 1.6,
      hue,
      phase: random() * Math.PI * 2,
      driftX: (random() - 0.5) * 0.015,
      driftY: (random() - 0.5) * 0.015,
      share: 0.05,
      growthRate: 0,
      migrationPressure: 0
    });
  }

  const resources = Array.from({ length: 9 }, (_, index) => ({
    id: `resource-${index}`,
    x: random(),
    y: random(),
    radius: 0.14 + random() * 0.26,
    strength: clamp(region.resourceDensity * (0.5 + random() * 0.8)),
    phase: random() * Math.PI * 2
  }));

  return {
    agents,
    resources,
    signals,
    summary: {
      agentCount,
      totalPopulation,
      speciesCount,
      latestEventLabel: latestEvent?.eventLabel ?? null
    }
  };
}

function eventSignals(events: ChronicleEvent[], collapsed: boolean) {
  const signals = {
    mutation: 0,
    migration: 0,
    collapse: collapsed ? 0.9 : 0,
    catalyst: 0,
    recovery: 0
  };

  for (const event of events.slice(0, 8)) {
    const type = event.eventType.toLowerCase();
    const severity = clamp(event.severity / 5);
    if (type.includes("mutation") || type.includes("speciation") || type.includes("species")) {
      signals.mutation = Math.max(signals.mutation, severity);
    }
    if (type.includes("migration")) {
      signals.migration = Math.max(signals.migration, severity);
    }
    if (type.includes("collapse")) {
      signals.collapse = Math.max(signals.collapse, severity);
    }
    if (type.includes("catalyst") || type.includes("pulse") || type.includes("burst")) {
      signals.catalyst = Math.max(signals.catalyst, severity);
    }
    if (type.includes("recovery") || type.includes("resource")) {
      signals.recovery = Math.max(signals.recovery, severity * 0.85);
    }
  }

  return signals;
}

function seededRandom(seed: number) {
  let state = seed || 1;
  return () => {
    state = (state * 1664525 + 1013904223) >>> 0;
    return state / 4294967296;
  };
}

function hashString(value: string) {
  let hash = 2166136261;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function hashHue(value: string) {
  return hashString(value) % 360;
}

function clamp(value: number) {
  return Math.max(0, Math.min(1, value));
}
