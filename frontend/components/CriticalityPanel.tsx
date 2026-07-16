import type { CorrelationField, DiagnosticsData, ScaleFreeScan } from "@/lib/types";

/**
 * Below this many region pairs, a point on the reach curve is an average over too
 * little to read. The count collapses toward the map's diagonal — two pairs at the
 * far corner of a 12x9 — which is how a curve normalised to 1 at zero distance ends
 * up reporting 1.15 out there. Everything past it is drawn faint.
 */
const TRUST_PAIRS = 100;

const VERDICT_COPY: Record<ScaleFreeScan["verdict"], { headline: string; note: string }> = {
  critical: {
    headline: "it flocks",
    note: "Reach grows with the world and the curves fall on top of each other — the starling result."
  },
  sub_critical: {
    headline: "no flocking",
    note: "The world grows, the reach does not. Alpha has a fixed patch size."
  },
  intermediate: {
    headline: "somewhere in between",
    note: "Reach grows with the world, but not fast enough to call it scale-free."
  },
  underpowered: {
    headline: "not measurable yet",
    note: "Too many sizes bottomed out at the smallest distance the grid can express, so the trend is fitted through upper bounds rather than measurements. More sizes and more seeds would settle it."
  },
  degenerate: {
    headline: "nothing to measure",
    note: "The field barely varies between regions, so there is no difference to correlate."
  },
  insufficient: {
    headline: "not measurable yet",
    note: "Too few world sizes completed to compare them."
  }
};

export function CriticalityPanel({ data }: { data: DiagnosticsData }) {
  const { universe, correlation, census, triggers, scaleFree } = data;
  const fields = Object.entries(correlation);
  const stability = correlation.stability;

  return (
    <div className="criticality">
      <section className="crit-plate crit-verdict-plate">
        <ScaleFreeVerdict scan={scaleFree} tick={universe.tick} />
      </section>

      <section className="crit-plate">
        <PlateHead
          title="How far does a region reach?"
          evidence={`${universe.regions} regions · ${pairTotal(stability)} pairs`}
        >
          Read the solid part of each line: that is where enough pairs of regions stand behind the
          average to trust it. Where the line goes faint, the map has run out of regions that far
          apart.
        </PlateHead>
        <div className="crit-multiples">
          {fields.map(([name, field]) => (
            <ReachCell key={name} name={name} field={field} />
          ))}
        </div>
      </section>

      {stability ? (
        <section className="crit-plate">
          <PlateHead title="Why the far end of those curves is fiction" evidence="pairs per distance">
            Every point on a reach curve is an average over the pairs of regions that far apart. At
            middling distances there are hundreds. At opposite corners of the map there are two — and
            an average of two numbers is not an average, it is two numbers.
          </PlateHead>
          <PairProfile field={stability} />
        </section>
      ) : null}

      {scaleFree ? (
        <section className="crit-plate">
          <PlateHead
            title="The deciding test: grow the world"
            evidence={`${scaleFree.points.length} sizes · 1 seed · measured at tick ${scaleFree.measuredAtTick}`}
          >
            Build the same universe at four sizes and watch what the reach does. If Alpha were poised
            the way a flock is, reach would grow right along with the map and this line would run
            flat.
          </PlateHead>
          <ScanChart scan={scaleFree} />
        </section>
      ) : null}

      <section className="crit-plate">
        <PlateHead
          title="The second opinion: patch sizes"
          evidence={`${census.domainSizePowerLaw.domains} patches · ${census.domainSizePowerLaw.distinctSizes} distinct sizes`}
        >
          A system at a tipping point makes patches of every size — many tiny, a few enormous. One
          with a fixed scale makes patches of roughly one size.
        </PlateHead>
        <PatchHistogram histogram={census.domainSizePowerLaw.histogram} />
        <div className="crit-withheld-grid">
          <Withheld
            label="The curve's exponent"
            why={`Needs roughly 50+ patches across 10+ distinct sizes. Alpha has ${census.domainSizePowerLaw.domains} in ${census.domainSizePowerLaw.distinctSizes}.`}
            aside="a line through three points is not a distribution"
          />
          <Withheld
            label="How well the curve fits"
            why="Most of those points sit at the same height, and any line through them looks perfect."
            aside="the usual fit score was never valid for this shape anyway"
          />
        </div>
      </section>

      <section className="crit-plate">
        <PlateHead
          title="Has anything started repeating?"
          evidence={`${universe.species} species · ${universe.regions} regions`}
        >
          Plain counts — nothing inferred, so nothing to over-claim. When a world starts organising,
          shapes recur: unrelated lineages arrive at the same body plan.
        </PlateHead>
        <CensusTiles census={census} species={universe.species} />
      </section>

      <section className="crit-plate">
        <PlateHead title="What we are not showing you, and why" evidence="withheld">
          There is a table that asks a fair question: given these conditions, how much likelier is
          this pattern? The arithmetic is right; the sample is not. When a pattern turns up exactly
          once, under conditions that also turn up exactly once, the formula can only return the
          total number of observations.
        </PlateHead>
        <TriggerTable triggers={triggers} />
      </section>
    </div>
  );
}

function PlateHead({
  title,
  evidence,
  children
}: {
  title: string;
  evidence: string;
  children: React.ReactNode;
}) {
  return (
    <div className="crit-plate-head">
      <div className="crit-plate-row">
        <h2>{title}</h2>
        {/* Every panel declares its evidence; it is the page's whole argument. */}
        <span className="crit-evidence">{evidence}</span>
      </div>
      <p>{children}</p>
    </div>
  );
}

function ScaleFreeVerdict({ scan, tick }: { scan: ScaleFreeScan | null; tick: number }) {
  if (!scan) {
    return (
      <>
        <p className="eyebrow">The answer</p>
        <p className="crit-answer">Not measured yet.</p>
        <p className="crit-answer-note">
          The deciding test rebuilds this universe at four sizes and replays every tick, so it runs on
          the simulation worker rather than when you open the page. No result has been parked yet —
          which is a blank, not a verdict.
        </p>
      </>
    );
  }
  const copy = VERDICT_COPY[scan.verdict];
  const stale = tick - scan.measuredAtTick;
  return (
    <>
      <p className="eyebrow">The answer</p>
      <p className="crit-answer">{copy.headline}.</p>
      <p className="crit-answer-note">{copy.note}</p>
      <p className="crit-provenance">
        Measured at tick {scan.measuredAtTick.toLocaleString()}
        {stale > 0 ? ` · ${stale.toLocaleString()} ticks ago` : null} · took{" "}
        {(scan.durationMs / 1000).toFixed(1)}s
      </p>
    </>
  );
}

function ReachCell({ name, field }: { name: string; field: CorrelationField }) {
  if (field.degenerate) {
    return (
      <div className="crit-cell">
        <div className="crit-cell-head">
          <span className="crit-cell-title">{name}</span>
        </div>
        <p className="crit-cell-note">No variance between regions — there is nothing to correlate.</p>
      </div>
    );
  }

  const W = 240;
  const H = 118;
  const ml = 30;
  const mr = 8;
  const mt = 10;
  const mb = 20;
  const iw = W - ml - mr;
  const ih = H - mt - mb;
  const yMax = 0.28;
  const pairs = new Map(field.pairs);
  const rMax = Math.max(...field.curve.map(([r]) => r));
  const trusted = field.curve.filter(([r]) => (pairs.get(r) ?? 0) >= TRUST_PAIRS);
  const rTrust = trusted.length ? Math.max(...trusted.map(([r]) => r)) : rMax;

  const x = (r: number) => ml + ((r - 1) / Math.max(1, rMax - 1)) * iw;
  const y = (v: number) =>
    mt + ih / 2 - (Math.max(-yMax, Math.min(yMax, v)) / yMax) * (ih / 2);
  const path = (from: number, to: number) =>
    field.curve
      .filter(([r]) => r >= from && r <= to)
      .map(([r, c], i) => `${i ? "L" : "M"}${x(r)} ${y(c)}`)
      .join("");

  return (
    <div className="crit-cell">
      <div className="crit-cell-head">
        <span className="crit-cell-title">{name}</span>
        <span className="crit-cell-value">
          reach {field.xiFloored ? `< ${field.curve[0][0]}` : field.xi}
        </span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Reach curve for ${name}`}>
        <rect x={x(rTrust)} y={mt} width={W - mr - x(rTrust)} height={ih} className="crit-untrusted" />
        <line x1={ml} x2={W - mr} y1={y(0)} y2={y(0)} className="crit-axis" />
        <path d={path(1, rTrust)} className="crit-line" />
        <path d={path(rTrust, rMax)} className="crit-line crit-line-faint" />
        {!field.xiFloored ? (
          <line x1={x(field.xi)} x2={x(field.xi)} y1={mt} y2={mt + ih} className="crit-marker" />
        ) : null}
        {[1, Math.round(rMax / 2), rMax].map((r) => (
          <text key={r} x={x(r)} y={H - 6} textAnchor="middle" className="crit-tick">
            {r}
          </text>
        ))}
        <text x={ml - 5} y={y(0) + 3} textAnchor="end" className="crit-tick">
          0
        </text>
      </svg>
      <p className="crit-cell-note">
        {field.xiFloored
          ? "Flat noise — a region barely influences its neighbour. Reach is under one region, which is the smallest distance this grid can express."
          : "A real reach: agreement survives past the region next door."}
      </p>
    </div>
  );
}

function PairProfile({ field }: { field: CorrelationField }) {
  const W = 1000;
  const H = 150;
  const ml = 46;
  const mr = 12;
  const mt = 12;
  const mb = 30;
  const iw = W - ml - mr;
  const ih = H - mt - mb;
  const max = Math.max(...field.pairs.map(([, n]) => n));
  const bw = iw / field.pairs.length;
  const yT = mt + ih - (TRUST_PAIRS / max) * ih;

  return (
    <div className="crit-scroll">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="How many region pairs exist at each distance">
        <line x1={ml} x2={ml + iw} y1={mt + ih} y2={mt + ih} className="crit-axis" />
        <line x1={ml} x2={ml + iw} y1={yT} y2={yT} className="crit-threshold" />
        <text x={ml + 4} y={yT - 5} className="crit-threshold-label">
          below {TRUST_PAIRS} pairs — not enough
        </text>
        {field.pairs.map(([r, n], i) => {
          const h = (n / max) * ih;
          return (
            <rect
              key={r}
              x={ml + i * bw + 1}
              y={mt + ih - h}
              width={bw - 2}
              height={Math.max(h, 1)}
              rx={2}
              className={n >= TRUST_PAIRS ? "crit-bar" : "crit-bar crit-bar-faint"}
            >
              <title>
                {r} apart — {n} pairs
              </title>
            </rect>
          );
        })}
        {field.pairs
          .filter((_, i) => i % 3 === 0 || i === field.pairs.length - 1)
          .map(([r]) => (
            <text
              key={r}
              x={ml + (field.pairs.findIndex(([rr]) => rr === r) + 0.5) * bw}
              y={H - 10}
              textAnchor="middle"
              className="crit-tick"
            >
              {r}
            </text>
          ))}
      </svg>
    </div>
  );
}

function ScanChart({ scan }: { scan: ScaleFreeScan }) {
  const W = 1000;
  const H = 210;
  const ml = 52;
  const mr = 150;
  const mt = 16;
  const mb = 34;
  const iw = W - ml - mr;
  const ih = H - mt - mb;
  const yMax = Math.max(0.18, ...scan.points.map((p) => p.xiOverL)) * 1.15;
  const x = (i: number) => ml + (i / Math.max(1, scan.points.length - 1)) * iw;
  const y = (v: number) => mt + ih - (v / yMax) * ih;
  const ref = scan.points[0]?.xiOverL ?? 0;

  return (
    <div className="crit-scroll">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Reach relative to world size, against world size">
        <line x1={ml} x2={ml + iw} y1={y(ref)} y2={y(ref)} className="crit-reference" />
        <text x={ml + iw + 10} y={y(ref) + 4} className="crit-reference-label">
          flat = flocking
        </text>
        <path
          d={scan.points.map((p, i) => `${i ? "L" : "M"}${x(i)} ${y(p.xiOverL)}`).join("")}
          className="crit-line"
        />
        {scan.points.map((p, i) => (
          <g key={p.L}>
            <circle
              cx={x(i)}
              cy={y(p.xiOverL)}
              r={5.5}
              className={p.xiFloored ? "crit-dot crit-dot-floored" : "crit-dot"}
            >
              <title>
                {p.L} regions wide — reach {p.xiFloored ? "under 1, at floor" : p.xi}
              </title>
            </circle>
            <text x={x(i)} y={H - 12} textAnchor="middle" className="crit-tick">
              {p.L} wide
            </text>
            <text x={x(i)} y={y(p.xiOverL) - 13} textAnchor="middle" className="crit-point-label">
              {p.xiOverL.toFixed(3)}
            </text>
          </g>
        ))}
        <text x={ml + iw + 10} y={mt + 14} className="crit-legend">
          ○ reach at floor
        </text>
      </svg>
    </div>
  );
}

function PatchHistogram({ histogram }: { histogram: Array<[number, number]> }) {
  const max = Math.max(...histogram.map(([, c]) => c), 1);
  return (
    <div className="crit-patches">
      {histogram.map(([size, count]) => (
        <div className="crit-patch" key={size}>
          <span className="crit-patch-count">{count}</span>
          <div className="crit-patch-bar" style={{ height: `${(count / max) * 100}%` }} />
          <span className="crit-tick">
            {size} region{size > 1 ? "s" : ""}
          </span>
        </div>
      ))}
      <p className="crit-patch-note">…and that is the whole sample.</p>
    </div>
  );
}

function Withheld({ label, why, aside }: { label: string; why: string; aside: string }) {
  return (
    <div className="crit-withheld">
      <span className="crit-withheld-label">{label}</span>
      {/* Deliberately blank, not greyed: a faded number is still read and quoted. */}
      <span className="crit-withheld-slot" aria-label="withheld">
        —
      </span>
      <p className="crit-withheld-why">{why}</p>
      <p className="crit-withheld-aside">{aside}</p>
    </div>
  );
}

function CensusTiles({
  census,
  species
}: {
  census: DiagnosticsData["census"];
  species: number;
}) {
  const topMorph = census.morphotypes.top[0];
  const topSpatial = census.spatialMotifs.top[0];
  return (
    <div className="crit-tiles">
      <Tile
        k="Body plans"
        v={`${census.morphotypes.distinct} / ${species}`}
        d="how many distinct shapes across every species"
      />
      <Tile
        k="Most-shared body plan"
        v={`${topMorph?.species ?? 0} species`}
        d="how many species share the commonest shape"
      />
      <Tile
        k="Convergence"
        v={census.morphotypes.convergenceIndex.toFixed(2)}
        d="0 means no two lineages have met on a shape"
      />
      <Tile
        k="Commonest map arrangement"
        v={`${topSpatial?.count ?? 0} regions`}
        d={`of ${census.spatialMotifs.distinct} arrangements`}
      />
    </div>
  );
}

function Tile({ k, v, d }: { k: string; v: string; d: string }) {
  return (
    <div className="crit-tile">
      <span className="crit-tile-k">{k}</span>
      <span className="crit-tile-v">{v}</span>
      <span className="crit-tile-d">{d}</span>
    </div>
  );
}

function TriggerTable({ triggers }: { triggers: DiagnosticsData["triggers"] }) {
  return (
    <div className="crit-scroll">
      <table className="crit-table">
        <thead>
          <tr>
            <th>Pattern family</th>
            <th>Observations</th>
            <th>Rows</th>
            <th>Seen only once</th>
            <th>Top score</th>
            <th>Reportable</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(triggers.families).map(([name, family]) => (
            <tr key={name}>
              <td>{name}</td>
              <td className="crit-num">{family.instances}</td>
              <td className="crit-num">{family.rows}</td>
              <td className="crit-num">
                {family.singletonRows} / {family.rows}
              </td>
              <td className="crit-num">
                <span className="crit-struck">{family.topLift ?? "—"}</span>
                {/* lift can only equal n when support is 1 — the artefact, shown. */}
                {family.topLiftEqualsInstances ? <span className="crit-equals"> = observations</span> : null}
              </td>
              <td className="crit-num">
                {family.reportable.length > 0 ? family.reportable.length : "none"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="crit-table-note">
        Read the last two columns together: where the top score equals the number of observations,
        the “discovery” is the sample size wearing a lab coat. Nothing below {triggers.minSupport}{" "}
        sightings reaches this page at all — the gate is in the API, so no view can print it by
        accident.
      </p>
    </div>
  );
}

function pairTotal(field: CorrelationField | undefined) {
  if (!field) return 0;
  return field.pairs.reduce((sum, [, n]) => sum + n, 0).toLocaleString();
}
