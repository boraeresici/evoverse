import Link from "next/link";
import type { CSSProperties } from "react";
import type { DynamicReportData, RegionDetail, SpeciesSummary } from "@/lib/types";

type RegionInvestigationPanelProps = {
  report: DynamicReportData | null;
  populations: RegionDetail["populations"];
  species: SpeciesSummary[];
};

const trendMetrics = [
  { key: "energyLevel", label: "Energy", color: "var(--blue)" },
  { key: "resourceDensity", label: "Resources", color: "var(--amber)" },
  { key: "stability", label: "Stability", color: "var(--green)" }
];

export function RegionInvestigationPanel({
  report,
  populations,
  species
}: RegionInvestigationPanelProps) {
  const totalPopulation = populations.reduce((total, item) => total + item.population, 0);
  const speciesById = new Map(species.map((item) => [item.id, item]));

  return (
    <section className="region-investigation">
      <div className="section-heading compact-heading">
        <div>
          <p className="eyebrow">Investigation</p>
          <h2>Region Signals</h2>
        </div>
      </div>

      <div className="region-trend-grid">
        {trendMetrics.map((metric) => (
          <article
            className="region-trend-card"
            key={metric.key}
            style={{ "--metric-color": metric.color } as CSSProperties}
          >
            <header>
              <span>{metric.label}</span>
              <strong>{formatPercent(lastMetric(report, metric.key))}</strong>
            </header>
            {report ? (
              <TrendSvg metricKey={metric.key} report={report} />
            ) : (
              <p>Trend data is warming up.</p>
            )}
          </article>
        ))}
      </div>

      <div className="region-composition-grid">
        <article className="population-composition">
          <h3>Population Composition</h3>
          <div className="composition-list">
            {populations.map((population) => {
              const share = totalPopulation ? population.population / totalPopulation : 0;
              return (
                <Link href={`/species/${population.speciesId}`} key={population.speciesId}>
                  <span>
                    <strong>{population.speciesName}</strong>
                    <small>{Math.round(share * 100)}% share</small>
                  </span>
                  <i>
                    <b style={{ width: `${Math.max(4, Math.round(share * 100))}%` }} />
                  </i>
                  <em>{population.population.toLocaleString()}</em>
                </Link>
              );
            })}
          </div>
        </article>

        <article className="related-species-panel">
          <h3>Related Species</h3>
          <div className="related-species-list">
            {populations.map((population) => {
              const item = speciesById.get(population.speciesId);
              return (
                <Link href={`/species/${population.speciesId}`} key={population.speciesId}>
                  <strong>{population.speciesName}</strong>
                  <span>{item ? `Generation ${item.generation}` : population.status}</span>
                  <small>{item?.parentSpeciesId ? `Parent ${item.parentSpeciesId}` : "Root lineage"}</small>
                </Link>
              );
            })}
          </div>
        </article>
      </div>
    </section>
  );
}

function TrendSvg({
  metricKey,
  report
}: {
  metricKey: string;
  report: DynamicReportData;
}) {
  const chart = chartGeometry(report.series, metricKey);
  return (
    <svg aria-label={`${metricKey} trend`} role="img" viewBox="0 0 420 140">
      <path className="chart-grid-line" d="M0 26 H420" />
      <path className="chart-grid-line" d="M0 70 H420" />
      <path className="chart-grid-line" d="M0 114 H420" />
      <polyline className="chart-line" fill="none" points={chart.points} />
      {chart.dots.map((dot) => (
        <circle cx={dot.x} cy={dot.y} key={`${dot.x}-${dot.y}`} r="4" />
      ))}
    </svg>
  );
}

function chartGeometry(
  series: DynamicReportData["series"],
  metricKey: string
) {
  const values = series.map((point) => Number(point.metrics[metricKey] ?? 0));
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const width = 420;
  const height = 104;
  const top = 18;
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
    dots
  };
}

function lastMetric(report: DynamicReportData | null, metricKey: string) {
  return Number(report?.current.metrics[metricKey] ?? 0);
}

function formatPercent(value: number) {
  return `${Math.round(value * 100)}%`;
}
