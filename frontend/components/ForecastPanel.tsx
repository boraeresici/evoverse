import { InfoTip } from "@/components/InfoTip";
import {
  buildPopulationFan,
  forecastGauges,
  type ForecastGauge,
  type PopulationFan
} from "@/lib/forecast";
import type { DynamicReportData, SpeciesSummary } from "@/lib/types";

type ForecastPanelProps = {
  species: SpeciesSummary;
  report: DynamicReportData | null;
};

const GAUGE_SIZE = 78;
const GAUGE_STROKE = 8;

export function ForecastPanel({ species, report }: ForecastPanelProps) {
  const gauges = forecastGauges(species.forecast);
  const fan = buildPopulationFan(species, report);

  return (
    <section className="forecast-panel" aria-label="Species forecast">
      <div className="forecast-gauges">
        {gauges.map((gauge) => (
          <Gauge key={gauge.key} gauge={gauge} />
        ))}
      </div>
      <PopulationFanChart fan={fan} />
    </section>
  );
}

function Gauge({ gauge }: { gauge: ForecastGauge }) {
  const radius = (GAUGE_SIZE - GAUGE_STROKE) / 2;
  const circumference = 2 * Math.PI * radius;
  const dash = gauge.value * circumference;
  const center = GAUGE_SIZE / 2;
  return (
    <article className={`forecast-gauge gauge-tone-${gauge.tone}`}>
      <svg
        className="gauge-svg"
        viewBox={`0 0 ${GAUGE_SIZE} ${GAUGE_SIZE}`}
        role="img"
        aria-label={`${gauge.label}: ${Math.round(gauge.value * 100)} percent`}
      >
        <circle className="gauge-track" cx={center} cy={center} r={radius} strokeWidth={GAUGE_STROKE} />
        <circle
          className="gauge-value"
          cx={center}
          cy={center}
          r={radius}
          strokeWidth={GAUGE_STROKE}
          strokeDasharray={`${dash} ${circumference - dash}`}
          strokeDashoffset={circumference / 4}
          transform={`rotate(-90 ${center} ${center})`}
        />
        <text className="gauge-percent" x={center} y={center + 1} textAnchor="middle">
          {Math.round(gauge.value * 100)}%
        </text>
      </svg>
      <div className="gauge-meta">
        <strong>{gauge.label}</strong>
        <span>{gauge.hint}</span>
      </div>
    </article>
  );
}

function PopulationFanChart({ fan }: { fan: PopulationFan }) {
  const width = 700;
  const height = 230;
  const padX = 10;
  const top = 14;
  const plotW = width - padX * 2;
  const plotH = height - top - 30;

  const allAges = [
    ...fan.history.map((point) => point.age),
    ...fan.projection.map((point) => point.age)
  ];
  const allValues = [
    ...fan.history.map((point) => point.population),
    ...fan.projection.map((point) => point.high)
  ];
  const minAge = Math.min(...allAges);
  const maxAge = Math.max(...allAges);
  const maxVal = Math.max(1, ...allValues);
  const ageSpan = maxAge - minAge || 1;

  const x = (age: number) => padX + ((age - minAge) / ageSpan) * plotW;
  const y = (value: number) => top + plotH - (value / maxVal) * plotH;

  const historyLine = fan.history.map((point) => `${round(x(point.age))},${round(y(point.population))}`);
  const midLine = fan.projection.map((point) => `${round(x(point.age))},${round(y(point.mid))}`);
  const bandPath = buildBandPath(fan, x, y);
  const nowX = x(fan.nowAge);

  if (fan.history.length === 0 && fan.projection.length <= 1) {
    return <p className="forecast-fan-empty">Population forecast is waiting for snapshot coverage.</p>;
  }

  return (
    <div className="forecast-fan">
      <div className="forecast-fan-head">
        <h3>
          Population trajectory
          <InfoTip
            label="Population trajectory"
            text="The band right of the now line is an illustrative projection from forecast signals (net expansion minus extinction, widening with mutation volatility) — a visualization, not a backend prediction."
          />
        </h3>
        <span>History + illustrative forecast fan</span>
      </div>
      <svg
        className="forecast-fan-svg"
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label="Population history and forecast fan chart"
      >
        <line className="fan-grid" x1={padX} x2={width - padX} y1={y(maxVal)} y2={y(maxVal)} />
        <line className="fan-grid" x1={padX} x2={width - padX} y1={y(maxVal / 2)} y2={y(maxVal / 2)} />
        <line className="fan-grid" x1={padX} x2={width - padX} y1={y(0)} y2={y(0)} />

        {bandPath ? <path className="fan-band" d={bandPath} /> : null}
        {midLine.length ? (
          <polyline className="fan-mid" fill="none" points={midLine.join(" ")} />
        ) : null}
        {historyLine.length ? (
          <polyline className="fan-history" fill="none" points={historyLine.join(" ")} />
        ) : null}

        <line className="fan-now" x1={nowX} x2={nowX} y1={top} y2={top + plotH} />
        <text className="fan-now-label" x={nowX + 4} y={top + 10}>
          now
        </text>

        <text className="fan-axis" x={padX} y={height - 10}>
          Age {minAge.toLocaleString()}
        </text>
        <text className="fan-axis" x={width - padX} y={height - 10} textAnchor="end">
          Age {maxAge.toLocaleString()} (proj)
        </text>
      </svg>
      <div className="forecast-fan-legend" aria-hidden="true">
        <span className="fan-key history">
          <i />
          Observed
        </span>
        <span className="fan-key mid">
          <i />
          Projected median
        </span>
        <span className="fan-key band">
          <i />
          Confidence fan
        </span>
      </div>
    </div>
  );
}

function buildBandPath(
  fan: PopulationFan,
  x: (age: number) => number,
  y: (value: number) => number
): string | null {
  if (fan.projection.length < 2) {
    return null;
  }
  const highs = fan.projection.map((point) => `${round(x(point.age))},${round(y(point.high))}`);
  const lows = fan.projection
    .slice()
    .reverse()
    .map((point) => `${round(x(point.age))},${round(y(point.low))}`);
  return `M${highs.join(" L")} L${lows.join(" L")} Z`;
}

function round(value: number): number {
  return Math.round(value * 100) / 100;
}
