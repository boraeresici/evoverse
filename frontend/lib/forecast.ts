import type { DynamicReportData, SpeciesSummary } from "./types";

export type ForecastTone = "extinction" | "dominance" | "expansion" | "mutation";

export type ForecastGauge = {
  key: ForecastTone;
  label: string;
  value: number;
  tone: ForecastTone;
  hint: string;
};

export function forecastGauges(forecast: SpeciesSummary["forecast"]): ForecastGauge[] {
  return [
    {
      key: "extinction",
      label: "Extinction risk",
      value: clamp01(forecast.extinctionRisk),
      tone: "extinction",
      hint: riskHint(forecast.extinctionRisk)
    },
    {
      key: "dominance",
      label: "Dominance",
      value: clamp01(forecast.dominanceProbability),
      tone: "dominance",
      hint: probabilityHint(forecast.dominanceProbability)
    },
    {
      key: "expansion",
      label: "Expansion",
      value: clamp01(forecast.expansionPressure),
      tone: "expansion",
      hint: probabilityHint(forecast.expansionPressure)
    },
    {
      key: "mutation",
      label: "Mutation volatility",
      value: clamp01(forecast.mutationVolatility),
      tone: "mutation",
      hint: volatilityHint(forecast.mutationVolatility)
    }
  ];
}

export type FanPoint = {
  age: number;
  mid: number;
  low: number;
  high: number;
};

export type PopulationHistoryPoint = {
  age: number;
  population: number;
};

export type PopulationFan = {
  history: PopulationHistoryPoint[];
  projection: FanPoint[];
  nowAge: number;
  nowPopulation: number;
};

const PROJECTION_STEPS = 8;

/**
 * Illustrative forward projection of a species population from its forecast
 * signals — NOT a backend simulation. The central trajectory follows net
 * (expansion - extinction) pressure; the fan widens with mutation volatility and
 * extinction risk over time so the forecast reads as a trajectory, not a number.
 */
export function buildPopulationFan(
  species: SpeciesSummary,
  report: DynamicReportData | null
): PopulationFan {
  const history: PopulationHistoryPoint[] = (report?.series ?? [])
    .map((point) => ({
      age: point.worldAge,
      population: Number(point.metrics.populationCount ?? 0)
    }))
    .filter((point) => Number.isFinite(point.age));

  const nowAge = history.length ? history[history.length - 1].age : species.emergedAtWorldAge;
  const nowPopulation = history.length
    ? history[history.length - 1].population
    : species.population;

  const { extinctionRisk, expansionPressure, mutationVolatility } = species.forecast;
  const netRate = (expansionPressure - extinctionRisk) * 0.08;

  // Step size mirrors the average spacing of the observed history so the fan
  // extends on the same time scale.
  const stepAge = historyStep(history);

  const projection: FanPoint[] = [{ age: nowAge, mid: nowPopulation, low: nowPopulation, high: nowPopulation }];
  for (let step = 1; step <= PROJECTION_STEPS; step += 1) {
    const mid = nowPopulation * Math.pow(1 + netRate, step);
    const spread = Math.min(
      0.95,
      mutationVolatility * 0.55 * Math.sqrt(step) + extinctionRisk * 0.09 * step
    );
    projection.push({
      age: Math.round(nowAge + step * stepAge),
      mid: Math.max(0, Math.round(mid)),
      low: Math.max(0, Math.round(mid * (1 - spread))),
      high: Math.max(0, Math.round(mid * (1 + spread * 0.7)))
    });
  }

  return { history, projection, nowAge, nowPopulation };
}

function historyStep(history: PopulationHistoryPoint[]): number {
  if (history.length < 2) {
    return 24;
  }
  const span = history[history.length - 1].age - history[0].age;
  return Math.max(1, span / (history.length - 1));
}

function riskHint(value: number): string {
  if (value >= 0.66) return "Critical";
  if (value >= 0.33) return "Elevated";
  return "Stable";
}

function probabilityHint(value: number): string {
  if (value >= 0.66) return "Strong";
  if (value >= 0.33) return "Moderate";
  return "Weak";
}

function volatilityHint(value: number): string {
  if (value >= 0.66) return "Turbulent";
  if (value >= 0.33) return "Shifting";
  return "Steady";
}

function clamp01(value: number): number {
  return Math.max(0, Math.min(1, Number(value) || 0));
}
