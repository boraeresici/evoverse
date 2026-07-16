import Link from "next/link";
import type { CSSProperties } from "react";
import { Activity, ArrowRight, BarChart3, Gauge, Layers3 } from "lucide-react";
import type {
  DynamicReportData,
  DynamicReportDelta,
  DynamicReportPoint,
  DynamicReportScope,
  RegionSummary,
  SpeciesSummary
} from "@/lib/types";

type MetricDefinition = {
  key: string;
  label: string;
  format: "integer" | "decimal" | "percent" | "state";
  color: string;
};

type DynamicReportPanelProps = {
  report: DynamicReportData;
  regions: RegionSummary[];
  species: SpeciesSummary[];
  selectedRegionId: string | null;
  selectedSpeciesId: string | null;
};

const REPORT_METRICS: Record<DynamicReportScope, MetricDefinition[]> = {
  universe: [
    { key: "populationCount", label: "Population", format: "integer", color: "var(--green)" },
    { key: "speciesCount", label: "Species", format: "integer", color: "var(--cyan)" },
    { key: "eventCount", label: "Events", format: "integer", color: "var(--blue)" },
    {
      key: "collapsedRegionCount",
      label: "Collapsed Regions",
      format: "integer",
      color: "var(--brick)"
    },
    { key: "stabilityIndex", label: "Stability", format: "percent", color: "var(--amber)" }
  ],
  region: [
    { key: "populationCount", label: "Population", format: "integer", color: "var(--green)" },
    { key: "speciesCount", label: "Species", format: "integer", color: "var(--cyan)" },
    { key: "energyLevel", label: "Energy", format: "percent", color: "var(--blue)" },
    { key: "resourceDensity", label: "Resources", format: "percent", color: "var(--amber)" },
    { key: "stability", label: "Stability", format: "percent", color: "var(--brick)" },
    { key: "collapsed", label: "Region State", format: "state", color: "var(--brick)" }
  ],
  species: [
    { key: "populationCount", label: "Population", format: "integer", color: "var(--green)" },
    { key: "regionCount", label: "Regions", format: "integer", color: "var(--cyan)" },
    { key: "generation", label: "Generation", format: "integer", color: "var(--blue)" },
    { key: "traitStrength", label: "Trait Strength", format: "percent", color: "var(--amber)" }
  ],
  population: [
    { key: "populationCount", label: "Population", format: "integer", color: "var(--green)" },
    {
      key: "energyConsumption",
      label: "Energy Use",
      format: "decimal",
      color: "var(--blue)"
    },
    { key: "growthRate", label: "Growth", format: "percent", color: "var(--cyan)" },
    {
      key: "migrationPressure",
      label: "Migration",
      format: "percent",
      color: "var(--amber)"
    }
  ]
};

export function DynamicReportPanel({
  report,
  regions,
  species,
  selectedRegionId,
  selectedSpeciesId
}: DynamicReportPanelProps) {
  const metrics = availableMetrics(report);
  const selectedRegion = regions.find((region) => region.id === selectedRegionId);
  const selectedSpecies = species.find((item) => item.id === selectedSpeciesId);

  return (
    <>
      <section className="report-hero">
        <div>
          <p className="eyebrow">Dynamic Report</p>
          <h1>Alpha Progress Lens</h1>
          <p>
            Snapshot comparison across current and historical Alpha state, rendered from the same
            backend report model for universe, region, species, and population scopes.
          </p>
        </div>
        <div className="report-coverage" aria-label="Report coverage">
          <span>
            <Layers3 size={16} aria-hidden="true" />
            {report.coverage.seriesCount}/{report.coverage.totalSnapshots} snapshots
          </span>
          <span>
            <Activity size={16} aria-hidden="true" />
            Age {report.baseline.worldAge.toLocaleString()} to{" "}
            {report.current.worldAge.toLocaleString()}
          </span>
          <span>
            <Gauge size={16} aria-hidden="true" />
            Limit {report.filters.limit}
          </span>
        </div>
      </section>

      <ReportControls
        report={report}
        regions={regions}
        species={species}
        selectedRegionId={selectedRegionId}
        selectedSpeciesId={selectedSpeciesId}
      />

      <section className="report-context">
        <span>
          Scope <strong>{formatScope(report.scope.type)}</strong>
        </span>
        <Link href="/compare">
          Compare Regions
          <ArrowRight size={15} aria-hidden="true" />
        </Link>
        {selectedRegion ? (
          <Link href={`/regions/${selectedRegion.id}`}>
            Region {selectedRegion.id}
            <ArrowRight size={15} aria-hidden="true" />
          </Link>
        ) : null}
        {selectedSpecies ? (
          <Link href={`/species/${selectedSpecies.id}`}>
            Species {selectedSpecies.name}
            <ArrowRight size={15} aria-hidden="true" />
          </Link>
        ) : null}
      </section>

      <section className="report-summary-grid">
        {metrics.map((metric) => (
          <MetricSummary
            delta={report.delta}
            key={metric.key}
            metric={metric}
            point={report.current}
          />
        ))}
      </section>

      <section className="report-chart-grid">
        {metrics.map((metric) => (
          <MetricTrend
            delta={report.delta}
            key={metric.key}
            metric={metric}
            series={report.series}
          />
        ))}
      </section>
    </>
  );
}

function ReportControls({
  report,
  regions,
  species,
  selectedRegionId,
  selectedSpeciesId
}: DynamicReportPanelProps) {
  return (
    <form action="/reports" className="report-controls">
      <label>
        <span>Scope</span>
        <select name="scope" defaultValue={report.scope.type}>
          <option value="universe">Universe</option>
          <option value="region">Region</option>
          <option value="species">Species</option>
          <option value="population">Population</option>
        </select>
      </label>
      <label>
        <span>Region</span>
        <select name="regionId" defaultValue={selectedRegionId ?? ""}>
          {regions.map((region) => (
            <option key={region.id} value={region.id}>
              {region.id} / {region.dominantSpeciesName ?? "Unclaimed"}
            </option>
          ))}
        </select>
      </label>
      <label>
        <span>Species</span>
        <select name="speciesId" defaultValue={selectedSpeciesId ?? ""}>
          {species.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        <span>Snapshots</span>
        <input min={1} max={50} name="limit" type="number" defaultValue={report.filters.limit} />
      </label>
      <button className="primary-action report-apply" type="submit">
        <BarChart3 size={17} aria-hidden="true" />
        Apply
      </button>
    </form>
  );
}

function MetricSummary({
  delta,
  metric,
  point
}: {
  delta: DynamicReportDelta;
  metric: MetricDefinition;
  point: DynamicReportPoint;
}) {
  return (
    <article className="report-summary-card">
      <span>{metric.label}</span>
      <strong>{formatMetricValue(point.metrics[metric.key], metric)}</strong>
      <small>{formatDelta(delta[metric.key], metric)}</small>
    </article>
  );
}

function MetricTrend({
  delta,
  metric,
  series
}: {
  delta: DynamicReportDelta;
  metric: MetricDefinition;
  series: DynamicReportPoint[];
}) {
  const chart = chartGeometry(series, metric.key);

  return (
    <article
      className="report-chart-card"
      style={{ "--metric-color": metric.color } as CSSProperties}
    >
      <header>
        <div>
          <p className="eyebrow">{metric.label}</p>
          <h2>{formatMetricValue(chart.currentValue, metric)}</h2>
        </div>
        <span>{formatDelta(delta[metric.key], metric)}</span>
      </header>
      <svg aria-label={`${metric.label} trend`} role="img" viewBox="0 0 520 190">
        <path className="chart-grid-line" d="M0 32 H520" />
        <path className="chart-grid-line" d="M0 95 H520" />
        <path className="chart-grid-line" d="M0 158 H520" />
        <polyline className="chart-line" fill="none" points={chart.points} />
        {chart.dots.map((dot) => (
          <circle cx={dot.x} cy={dot.y} key={`${dot.x}-${dot.y}`} r="4.5" />
        ))}
      </svg>
      <footer>
        <span>Age {chart.startAge.toLocaleString()}</span>
        <span>Age {chart.endAge.toLocaleString()}</span>
      </footer>
    </article>
  );
}

function availableMetrics(report: DynamicReportData) {
  return REPORT_METRICS[report.scope.type].filter(
    (metric) => typeof report.current.metrics[metric.key] === "number"
  );
}

function chartGeometry(series: DynamicReportPoint[], metricKey: string) {
  const values = series.map((point) => Number(point.metrics[metricKey] ?? 0));
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const width = 520;
  const height = 150;
  const top = 20;
  const dots = series.map((point, index) => {
    const x = series.length === 1 ? width / 2 : (index / (series.length - 1)) * width;
    const value = Number(point.metrics[metricKey] ?? 0);
    const y = top + height - ((value - min) / range) * height;
    return {
      x: roundChartCoordinate(x),
      y: roundChartCoordinate(y),
      value
    };
  });

  return {
    points: dots.map((dot) => `${dot.x},${dot.y}`).join(" "),
    dots,
    currentValue: values[values.length - 1] ?? 0,
    startAge: series[0]?.worldAge ?? 0,
    endAge: series[series.length - 1]?.worldAge ?? 0
  };
}

function roundChartCoordinate(value: number) {
  return Math.round(value * 100) / 100;
}

function formatMetricValue(value: number | undefined, metric: MetricDefinition) {
  const numeric = Number(value ?? 0);
  if (metric.format === "state") {
    return numeric >= 1 ? "Collapsed" : "Stable";
  }
  if (metric.format === "percent") {
    return `${Math.round(numeric * 100)}%`;
  }
  if (metric.format === "decimal") {
    return numeric.toFixed(3);
  }
  return Math.round(numeric).toLocaleString();
}

function formatDelta(
  delta: DynamicReportDelta[string] | undefined,
  metric: MetricDefinition
) {
  if (!delta) {
    return "No baseline change";
  }
  if (metric.format === "state") {
    if (delta.absolute === 0) {
      return "No state change";
    }
    return delta.to >= 1 ? "Collapsed in range" : "Recovered in range";
  }

  const sign = delta.absolute > 0 ? "+" : "";
  const absolute =
    metric.format === "percent"
      ? `${sign}${Math.round(delta.absolute * 100)} pts`
      : `${sign}${Math.round(delta.absolute).toLocaleString()}`;
  const relative = delta.percent === null ? "" : ` / ${sign}${delta.percent}%`;
  return `${absolute}${relative}`;
}

function formatScope(scope: DynamicReportScope) {
  return scope.charAt(0).toUpperCase() + scope.slice(1);
}
