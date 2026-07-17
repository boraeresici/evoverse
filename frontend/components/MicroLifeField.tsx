"use client";

import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import {
  Gauge,
  Info,
  Layers3,
  Pause,
  Play,
  RadioTower,
  Sparkles,
  Sprout,
  ZoomIn,
  ZoomOut
} from "lucide-react";
import {
  buildMicroLifeProjection,
  type MicroLifeMode,
  type MicroLifeProjection
} from "@/lib/microLifeProjection";
import {
  advanceAgents,
  easeLife,
  liveAgentList,
  reconcileAgents,
  settleAgents,
  type LiveAgent
} from "@/lib/microLifeLife";
import { regionHandSign } from "@/lib/organismLens";
import type { ChronicleEvent, DynamicReportData, RegionDetail } from "@/lib/types";

type MicroLifeFieldProps = {
  region: RegionDetail["region"];
  populations: RegionDetail["populations"];
  events: ChronicleEvent[];
  report: DynamicReportData | null;
  compact?: boolean;
  eyebrow?: string;
  title?: string;
  /**
   * The close-up this field opens into — the Organism Lens in practice
   * (CHIRALITY_AND_MIND.md §8: the field is where "Inspect" lives). A slot
   * rather than a prop of the Lens itself, so the field stays a general
   * region view and never learns what a lineage's form is.
   */
  inspect?: ReactNode;
  /**
   * Hold the field still because the close-up in `inspect` is open. Two canvases
   * animating at once compete for the same attention, and while an observer is
   * reading a form the field is context, not the subject. The field is told only
   * that it is quieted — never why — so it stays a general region view.
   */
  quieted?: boolean;
};

const modes: Array<{
  id: MicroLifeMode;
  label: string;
  icon: typeof Sprout;
}> = [
  { id: "life", label: "Life", icon: Sprout },
  { id: "species", label: "Species", icon: Layers3 },
  { id: "resources", label: "Resources", icon: Gauge },
  { id: "events", label: "Events", icon: RadioTower }
];

const speeds = [0.55, 1, 1.65];

export function MicroLifeField({
  compact = false,
  events,
  eyebrow = "Micro View",
  inspect,
  populations,
  quieted = false,
  region,
  report,
  title = "Life Field"
}: MicroLifeFieldProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const shellRef = useRef<HTMLDivElement | null>(null);
  const poolRef = useRef<Map<string, LiveAgent>>(new Map());
  const lastTsRef = useRef(0);
  const [mode, setMode] = useState<MicroLifeMode>("life");
  const [playing, setPlaying] = useState(true);
  const [speedIndex, setSpeedIndex] = useState(1);
  const [zoom, setZoom] = useState(1);
  const [reducedMotion, setReducedMotion] = useState(false);
  const handSign = regionHandSign(region);
  const [showLegend, setShowLegend] = useState(false);
  const projection = useMemo(
    () =>
      buildMicroLifeProjection({
        events,
        populations,
        projectionContext: report?.current.tick ?? report?.current.worldAge ?? null,
        region
      }),
    [events, populations, region, report]
  );
  const reportBridge = useMemo(() => buildReportBridge(report), [report]);
  const speed = speeds[speedIndex];
  // Three ways the field can be still: the observer paused it, the OS asks for
  // reduced motion, or a close-up is open in front of it.
  const animating = playing && !reducedMotion && !quieted;

  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const updatePreference = () => setReducedMotion(media.matches);
    updatePreference();
    media.addEventListener("change", updatePreference);
    return () => media.removeEventListener("change", updatePreference);
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    const shell = shellRef.current;
    if (!canvas || !shell) {
      return;
    }
    const activeCanvas = canvas;
    const activeShell = shell;

    let frameId = 0;
    const context = activeCanvas.getContext("2d");
    if (!context) {
      return;
    }
    const activeContext = context;

    function resizeCanvas() {
      const rect = activeShell.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const width = Math.max(320, Math.round(rect.width));
      const height = Math.max(260, Math.round(rect.height));
      const pixelWidth = Math.round(width * dpr);
      const pixelHeight = Math.round(height * dpr);
      if (activeCanvas.width !== pixelWidth || activeCanvas.height !== pixelHeight) {
        activeCanvas.width = pixelWidth;
        activeCanvas.height = pixelHeight;
      }
      activeContext.setTransform(dpr, 0, 0, dpr, 0, 0);
      return { width, height };
    }

    const pool = poolRef.current;
    // Reconcile the persistent agent pool with the new projection: births spawn
    // in, vanished agents begin dying, survivors keep their position.
    reconcileAgents(pool, projection.agents);

    function draw(timestamp: number, advance: boolean) {
      const size = resizeCanvas();
      if (advance) {
        const dt = Math.max(0, Math.min(0.05, (timestamp - lastTsRef.current) / 1000));
        advanceAgents(pool, dt);
      }
      lastTsRef.current = timestamp;
      drawMicroLifeFrame({
        agents: liveAgentList(pool),
        context: activeContext,
        events,
        height: size.height,
        mode,
        projection,
        region,
        speed,
        timestamp,
        width: size.width,
        zoom
      });
    }

    function loop(timestamp: number) {
      draw(timestamp, true);
      if (animating) {
        frameId = window.requestAnimationFrame(loop);
      }
    }

    const observer = new ResizeObserver(() => draw(performance.now(), false));
    observer.observe(activeShell);
    if (animating) {
      lastTsRef.current = performance.now();
      frameId = window.requestAnimationFrame(loop);
    } else {
      // Static render: settle births/deaths instantly so nothing is mid-fade.
      settleAgents(pool);
      draw(performance.now(), false);
    }

    return () => {
      observer.disconnect();
      window.cancelAnimationFrame(frameId);
    };
  }, [animating, events, mode, projection, region, speed, zoom]);

  return (
    <section
      className={[
        "micro-life-panel",
        compact ? "compact" : "",
        quieted ? "quieted" : ""
      ]
        .filter(Boolean)
        .join(" ")}
      aria-labelledby="micro-life-title"
    >
      <div className="micro-life-header">
        <div>
          <p className="eyebrow">{eyebrow}</p>
          <h2 id="micro-life-title">{title}</h2>
        </div>
        <div className="micro-life-actions" aria-label="Micro life controls">
          <button
            aria-label={animating ? "Pause life field" : "Play life field"}
            // Held still by the close-up, so the control that cannot restart it
            // says so rather than looking broken when pressed.
            disabled={quieted}
            onClick={() => setPlaying((value) => !value)}
            title={quieted ? "Held still while the form is open" : animating ? "Pause" : "Play"}
            type="button"
          >
            {animating ? (
              <Pause size={16} aria-hidden="true" />
            ) : (
              <Play size={16} aria-hidden="true" />
            )}
          </button>
          <button
            aria-label="Zoom out life field"
            disabled={zoom <= 0.82}
            onClick={() => setZoom((value) => Math.max(0.8, Number((value - 0.2).toFixed(1))))}
            title="Zoom out"
            type="button"
          >
            <ZoomOut size={16} aria-hidden="true" />
          </button>
          <button
            aria-label="Zoom in life field"
            disabled={zoom >= 1.82}
            onClick={() => setZoom((value) => Math.min(1.8, Number((value + 0.2).toFixed(1))))}
            title="Zoom in"
            type="button"
          >
            <ZoomIn size={16} aria-hidden="true" />
          </button>
          <button
            aria-label="Change life field speed"
            onClick={() => setSpeedIndex((index) => (index + 1) % speeds.length)}
            title="Speed"
            type="button"
          >
            <Sparkles size={16} aria-hidden="true" />
            <span>{speed}x</span>
          </button>
          <button
            aria-label="Toggle visual legend"
            aria-pressed={showLegend}
            className={showLegend ? "active" : ""}
            onClick={() => setShowLegend((value) => !value)}
            title="Visual legend"
            type="button"
          >
            <Info size={16} aria-hidden="true" />
          </button>
        </div>
      </div>

      {showLegend ? <MicroLifeLegend /> : null}

      <div className="micro-life-mode-tabs" aria-label="Micro life mode">
        {modes.map((item) => {
          const Icon = item.icon;
          return (
            <button
              aria-pressed={mode === item.id}
              className={mode === item.id ? "active" : ""}
              key={item.id}
              onClick={() => setMode(item.id)}
              type="button"
            >
              <Icon size={16} aria-hidden="true" />
              {item.label}
            </button>
          );
        })}
      </div>

      <div className="micro-life-canvas-shell" ref={shellRef}>
        <canvas
          aria-label={`${region.id} sampled micro-life projection`}
          className="micro-life-canvas"
          ref={canvasRef}
          role="img"
        />
        <div className="micro-life-overlay" aria-hidden="true">
          <span>{projection.summary.agentCount} samples</span>
          <span>{projection.summary.speciesCount || 1} species</span>
          <span>{projection.summary.totalPopulation.toLocaleString()} aggregate population</span>
          {handSign !== 0 ? (
            <span className="micro-life-hand">
              {handSign > 0 ? "Right-handed" : "Left-handed"}
            </span>
          ) : null}
          {report ? <span>Age {report.current.worldAge.toLocaleString()}</span> : null}
          {quieted ? <span className="micro-life-quieted">Held still</span> : null}
        </div>
      </div>

      {inspect ?? null}

      <div className="micro-life-stats" aria-label="Life field signals">
        <span>Energy {Math.round(region.energyLevel * 100)}%</span>
        <span>Resources {Math.round(region.resourceDensity * 100)}%</span>
        <span>Stability {Math.round(region.stability * 100)}%</span>
        {projection.summary.latestEventLabel ? <span>{projection.summary.latestEventLabel}</span> : null}
      </div>
      {reportBridge.length ? (
        <div className="micro-life-report-bridge" aria-label="Baseline to current report drift">
          <span className="micro-life-report-window">
            Age {report?.baseline.worldAge.toLocaleString()} to {report?.current.worldAge.toLocaleString()}
          </span>
          {reportBridge.map((item) => (
            <span className={item.positive ? "positive" : item.negative ? "negative" : ""} key={item.key}>
              <strong>{item.label}</strong>
              <em>{item.value}</em>
            </span>
          ))}
        </div>
      ) : null}
    </section>
  );
}

const legendItems: Array<{ swatch: string; term: string; meaning: string }> = [
  { swatch: "hue", term: "Hue", meaning: "Species identity — each lineage keeps its color" },
  { swatch: "motion", term: "Drift", meaning: "Mobility & migration pressure" },
  { swatch: "cluster", term: "Clustering", meaning: "Cooperation & population share" },
  { swatch: "glow", term: "Brightness", meaning: "Energy & efficiency of the field" },
  { swatch: "birth", term: "Spark → fade in", meaning: "A birth as population grows" },
  { swatch: "death", term: "Fade out", meaning: "A death as population declines" },
  { swatch: "ripple", term: "Ripples", meaning: "Recent events radiating through the field" },
  { swatch: "collapse", term: "Red wash", meaning: "Region collapse" }
];

function MicroLifeLegend() {
  return (
    <div className="micro-life-legend" role="note" aria-label="Micro life visual legend">
      {legendItems.map((item) => (
        <div className="micro-legend-item" key={item.term}>
          <span className={`micro-legend-swatch swatch-${item.swatch}`} aria-hidden="true" />
          <div>
            <strong>{item.term}</strong>
            <small>{item.meaning}</small>
          </div>
        </div>
      ))}
    </div>
  );
}

function buildReportBridge(report: DynamicReportData | null) {
  if (!report) {
    return [];
  }

  return [
    {
      key: "populationCount",
      label: "Population",
      format: "integer"
    },
    {
      key: "energyLevel",
      label: "Energy",
      format: "percent"
    },
    {
      key: "resourceDensity",
      label: "Resources",
      format: "percent"
    },
    {
      key: "stability",
      label: "Stability",
      format: "percent"
    }
  ]
    .map((metric) => {
      const delta = report.delta[metric.key];
      if (!delta) {
        return null;
      }
      return {
        key: metric.key,
        label: metric.label,
        value: formatDelta(delta.absolute, metric.format),
        positive: delta.absolute > 0,
        negative: delta.absolute < 0
      };
    })
    .filter((item): item is NonNullable<typeof item> => Boolean(item));
}

function formatDelta(value: number, format: string) {
  const sign = value > 0 ? "+" : "";
  if (format === "percent") {
    return `${sign}${Math.round(value * 100)}pp`;
  }
  return `${sign}${Math.round(value).toLocaleString()}`;
}

function drawMicroLifeFrame({
  agents,
  context,
  events,
  height,
  mode,
  projection,
  region,
  speed,
  timestamp,
  width,
  zoom
}: {
  agents: LiveAgent[];
  context: CanvasRenderingContext2D;
  events: ChronicleEvent[];
  height: number;
  mode: MicroLifeMode;
  projection: MicroLifeProjection;
  region: RegionDetail["region"];
  speed: number;
  timestamp: number;
  width: number;
  zoom: number;
}) {
  const time = (timestamp / 1000) * speed;
  const fieldSize = Math.min(width, height);
  const left = (width - fieldSize) / 2;
  const top = (height - fieldSize) / 2;

  context.clearRect(0, 0, width, height);
  drawBackground(context, width, height, region, projection, time, mode);

  context.save();
  context.beginPath();
  context.roundRect(left, top, fieldSize, fieldSize, 10);
  context.clip();

  if (mode === "resources" || mode === "life") {
    drawResourceField(context, projection, left, top, fieldSize, time, mode);
  }
  drawAgents(context, agents, projection, region, left, top, fieldSize, time, zoom, mode);
  if (mode === "events") {
    drawEventSignals(context, events, projection, left, top, fieldSize, time);
  }
  drawFrame(context, left, top, fieldSize, region, projection, time);
  context.restore();
}

function drawBackground(
  context: CanvasRenderingContext2D,
  width: number,
  height: number,
  region: RegionDetail["region"],
  projection: MicroLifeProjection,
  time: number,
  mode: MicroLifeMode
) {
  const gradient = context.createLinearGradient(0, 0, width, height);
  const stability = Math.round(region.stability * 18);
  const energy = Math.round(region.energyLevel * 28);
  const resource = Math.round(region.resourceDensity * 18);
  gradient.addColorStop(0, `hsl(${154 + energy} 26% ${92 - stability}% / 1)`);
  gradient.addColorStop(0.52, `hsl(${186 + resource} 28% 93% / 1)`);
  gradient.addColorStop(1, region.collapsed ? "hsl(14 34% 83% / 1)" : "hsl(43 38% 91% / 1)");
  context.fillStyle = gradient;
  context.fillRect(0, 0, width, height);

  const pulse = 0.16 + projection.signals.mutation * 0.18 + projection.signals.catalyst * 0.16;
  context.fillStyle = `hsl(${mode === "events" ? 26 : 164} 58% 42% / ${pulse + Math.sin(time * 1.2) * 0.02})`;
  context.fillRect(0, 0, width, height);
}

function drawResourceField(
  context: CanvasRenderingContext2D,
  projection: MicroLifeProjection,
  left: number,
  top: number,
  fieldSize: number,
  time: number,
  mode: MicroLifeMode
) {
  for (const node of projection.resources) {
    const x = left + node.x * fieldSize + Math.cos(time * 0.42 + node.phase) * 8;
    const y = top + node.y * fieldSize + Math.sin(time * 0.36 + node.phase) * 8;
    const radius = fieldSize * node.radius;
    const alpha = (mode === "resources" ? 0.34 : 0.16) * node.strength;
    const gradient = context.createRadialGradient(x, y, 0, x, y, radius);
    gradient.addColorStop(0, `hsl(42 82% 54% / ${alpha})`);
    gradient.addColorStop(0.48, `hsl(172 48% 42% / ${alpha * 0.42})`);
    gradient.addColorStop(1, "transparent");
    context.fillStyle = gradient;
    context.beginPath();
    context.arc(x, y, radius, 0, Math.PI * 2);
    context.fill();
  }
}

function drawAgents(
  context: CanvasRenderingContext2D,
  agents: LiveAgent[],
  projection: MicroLifeProjection,
  region: RegionDetail["region"],
  left: number,
  top: number,
  fieldSize: number,
  time: number,
  zoom: number,
  mode: MicroLifeMode
) {
  const collapseFade = region.collapsed ? 0.42 : 1;
  // Once a region latches, its agents circulate in the direction of its hand:
  // the same fact the Lens draws as a coil, at the scale where a lineage is
  // still only a scatter of dots. Before the latch this is 1 — a racemic region
  // has no hand, so the field shows none (§8).
  const spin = regionHandSign(region) || 1;
  for (const agent of agents) {
    const presence = easeLife(agent.life);
    const jitter = region.collapsed ? 0.005 : 0.015 + agent.growthRate * 0.8;
    const centerX = 0.5 + (agent.x - 0.5) * zoom;
    const centerY = 0.5 + (agent.y - 0.5) * zoom;
    const flowX = Math.sin(time + agent.phase) * jitter + agent.driftX * Math.sin(time * 0.18);
    const flowY =
      Math.cos(time * 0.92 + agent.phase) * jitter * spin + agent.driftY * Math.cos(time * 0.18);
    const x = left + clamp01(centerX + flowX) * fieldSize;
    const y = top + clamp01(centerY + flowY) * fieldSize;
    const eventScale = 1 + projection.signals.mutation * 0.34 * Math.max(0, Math.sin(time * 2.4 + agent.phase));
    // Births scale up from a spark, deaths shrink away.
    const lifeScale = 0.28 + 0.72 * presence;
    const radius = Math.max(0.6, agent.radius * eventScale * lifeScale * (mode === "species" ? 1.22 : 1));
    const alpha = collapseFade * presence * (mode === "resources" ? 0.46 : 0.68 + agent.share * 0.25);
    const lightness = region.collapsed ? 42 : mode === "events" ? 58 : 46;

    context.fillStyle = `hsl(${agent.hue} 52% ${lightness}% / ${alpha})`;
    context.beginPath();
    context.arc(x, y, radius, 0, Math.PI * 2);
    context.fill();

    // Spawn halo: a brief expanding ring as a new agent is born.
    if (agent.state === "spawning" && presence < 0.98) {
      context.strokeStyle = `hsl(${agent.hue} 70% 52% / ${(1 - presence) * 0.5})`;
      context.lineWidth = 1;
      context.beginPath();
      context.arc(x, y, radius + (1 - presence) * 6, 0, Math.PI * 2);
      context.stroke();
    }

    if (mode === "species" && agent.share > 0.16 && agent.state === "alive") {
      context.strokeStyle = `hsl(${agent.hue} 62% 30% / ${0.28 * collapseFade})`;
      context.lineWidth = 1;
      context.stroke();
    }
  }
}

function drawEventSignals(
  context: CanvasRenderingContext2D,
  events: ChronicleEvent[],
  projection: MicroLifeProjection,
  left: number,
  top: number,
  fieldSize: number,
  time: number
) {
  const pulse = projection.signals.migration + projection.signals.catalyst + projection.signals.recovery;
  const eventCount = Math.max(1, Math.min(5, events.length));

  for (let index = 0; index < eventCount; index += 1) {
    const angle = (index / eventCount) * Math.PI * 2 + time * 0.34;
    const startX = left + fieldSize * (0.5 + Math.cos(angle) * 0.16);
    const startY = top + fieldSize * (0.5 + Math.sin(angle) * 0.16);
    const endX = left + fieldSize * (0.5 + Math.cos(angle) * (0.34 + pulse * 0.12));
    const endY = top + fieldSize * (0.5 + Math.sin(angle) * (0.34 + pulse * 0.12));
    context.strokeStyle = `hsl(${26 + index * 38} 70% 46% / ${0.24 + pulse * 0.24})`;
    context.lineWidth = 2;
    context.beginPath();
    context.moveTo(startX, startY);
    context.lineTo(endX, endY);
    context.stroke();
  }

  if (projection.signals.collapse > 0) {
    context.fillStyle = `hsl(12 58% 42% / ${0.12 + projection.signals.collapse * 0.18})`;
    context.fillRect(left, top, fieldSize, fieldSize);
  }
}

function drawFrame(
  context: CanvasRenderingContext2D,
  left: number,
  top: number,
  fieldSize: number,
  region: RegionDetail["region"],
  projection: MicroLifeProjection,
  time: number
) {
  const alpha = 0.26 + region.stability * 0.28 + Math.sin(time * 0.8) * 0.03;
  context.strokeStyle = `hsl(${region.collapsed ? 12 : 154} 48% 34% / ${alpha})`;
  context.lineWidth = 2;
  context.strokeRect(left + 1, top + 1, fieldSize - 2, fieldSize - 2);

  if (projection.signals.recovery > 0) {
    context.strokeStyle = `hsl(154 54% 38% / ${projection.signals.recovery * 0.38})`;
    context.lineWidth = 1;
    context.beginPath();
    context.arc(
      left + fieldSize / 2,
      top + fieldSize / 2,
      fieldSize * (0.18 + (Math.sin(time * 0.7) + 1) * 0.08),
      0,
      Math.PI * 2
    );
    context.stroke();
  }
}

function clamp01(value: number) {
  return Math.max(0, Math.min(1, value));
}
