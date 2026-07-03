import Link from "next/link";
import type { CSSProperties } from "react";
import type { DynamicReportData, RegionSummary } from "@/lib/types";

type RegionComparePanelProps = {
  regions: RegionSummary[];
  leftRegionId: string;
  rightRegionId: string;
  leftReport: DynamicReportData | null;
  rightReport: DynamicReportData | null;
};

const compareMetrics = [
  { key: "populationCount", label: "Population", format: "integer", color: "var(--green)" },
  { key: "speciesCount", label: "Species", format: "integer", color: "var(--cyan)" },
  { key: "energyLevel", label: "Energy", format: "percent", color: "var(--blue)" },
  { key: "resourceDensity", label: "Resources", format: "percent", color: "var(--amber)" },
  { key: "stability", label: "Stability", format: "percent", color: "var(--brick)" }
] as const;

export function RegionComparePanel({
  leftRegionId,
  leftReport,
  regions,
  rightRegionId,
  rightReport
}: RegionComparePanelProps) {
  const leftRegion = regions.find((region) => region.id === leftRegionId);
  const rightRegion = regions.find((region) => region.id === rightRegionId);

  return (
    <>
      <section className="report-hero">
        <div>
          <p className="eyebrow">Compare</p>
          <h1>Region Comparison</h1>
          <p>Compare two Alpha regions across population, species count, energy, resources, and stability.</p>
        </div>
        <div className="report-coverage" aria-label="Comparison coverage">
          <span>{leftRegionId}</span>
          <span>{rightRegionId}</span>
          <Link href="/reports">Dynamic Reports</Link>
        </div>
      </section>

      <form action="/compare" className="report-controls compare-controls">
        <label>
          <span>Region A</span>
          <select name="left" defaultValue={leftRegionId}>
            {regions.map((region) => (
              <option key={region.id} value={region.id}>
                {region.id} / {region.dominantSpeciesName ?? "Unclaimed"}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>Region B</span>
          <select name="right" defaultValue={rightRegionId}>
            {regions.map((region) => (
              <option key={region.id} value={region.id}>
                {region.id} / {region.dominantSpeciesName ?? "Unclaimed"}
              </option>
            ))}
          </select>
        </label>
        <button className="primary-action report-apply" type="submit">
          Compare
        </button>
      </form>

      <section className="compare-region-context">
        {leftRegion ? <RegionContext region={leftRegion} /> : null}
        {rightRegion ? <RegionContext region={rightRegion} /> : null}
      </section>

      <section className="compare-grid">
        {compareMetrics.map((metric) => (
          <article
            className="compare-card"
            key={metric.key}
            style={{ "--metric-color": metric.color } as CSSProperties}
          >
            <header>
              <span>{metric.label}</span>
              <strong>
                {formatValue(metricValue(leftReport, metric.key), metric.format)} /{" "}
                {formatValue(metricValue(rightReport, metric.key), metric.format)}
              </strong>
            </header>
            <div className="compare-bars">
              <CompareBar label={leftRegionId} value={metricValue(leftReport, metric.key)} />
              <CompareBar label={rightRegionId} value={metricValue(rightReport, metric.key)} />
            </div>
          </article>
        ))}
      </section>
    </>
  );
}

function RegionContext({ region }: { region: RegionSummary }) {
  return (
    <Link href={`/regions/${region.id}`}>
      <strong>{region.id}</strong>
      <span>{region.dominantSpeciesName ?? "Unclaimed"}</span>
      <small>
        {region.population.toLocaleString()} population / {region.biomeType.replaceAll("_", " ")}
      </small>
    </Link>
  );
}

function CompareBar({ label, value }: { label: string; value: number }) {
  const width = Math.max(4, Math.min(100, Math.round(normalize(value) * 100)));
  return (
    <div className="compare-bar-row">
      <span>{label}</span>
      <i>
        <b style={{ width: `${width}%` }} />
      </i>
      <em>{value.toLocaleString()}</em>
    </div>
  );
}

function metricValue(report: DynamicReportData | null, key: string) {
  return Number(report?.current.metrics[key] ?? 0);
}

function normalize(value: number) {
  if (value <= 1) {
    return value;
  }
  return Math.min(1, value / 50000);
}

function formatValue(value: number, format: "integer" | "percent") {
  if (format === "percent") {
    return `${Math.round(value * 100)}%`;
  }
  return Math.round(value).toLocaleString();
}
