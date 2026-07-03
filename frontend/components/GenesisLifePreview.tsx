"use client";

import { useEffect, useMemo, useRef, useState } from "react";

type GenesisAgent = {
  x: number;
  y: number;
  radius: number;
  hue: number;
  phase: number;
  speed: number;
  drift: number;
};

type GenesisResource = {
  x: number;
  y: number;
  radius: number;
  phase: number;
};

const grid = {
  columns: 5,
  rows: 4
};

export function GenesisLifePreview() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const shellRef = useRef<HTMLDivElement | null>(null);
  const [reducedMotion, setReducedMotion] = useState(false);
  const field = useMemo(() => buildGenesisField(), []);

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

    const context = canvas.getContext("2d");
    if (!context) {
      return;
    }

    const activeCanvas = canvas;
    const activeContext = context;
    const activeShell = shell;
    let frameId = 0;

    function resizeCanvas() {
      const rect = activeShell.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const width = Math.max(320, Math.round(rect.width));
      const height = Math.max(280, Math.round(rect.height));
      const pixelWidth = Math.round(width * dpr);
      const pixelHeight = Math.round(height * dpr);

      if (activeCanvas.width !== pixelWidth || activeCanvas.height !== pixelHeight) {
        activeCanvas.width = pixelWidth;
        activeCanvas.height = pixelHeight;
      }

      activeContext.setTransform(dpr, 0, 0, dpr, 0, 0);
      return { width, height };
    }

    function draw(timestamp: number) {
      const size = resizeCanvas();
      drawGenesisFrame({
        context: activeContext,
        field,
        height: size.height,
        reducedMotion,
        timestamp,
        width: size.width
      });
    }

    function loop(timestamp: number) {
      draw(timestamp);
      if (!reducedMotion) {
        frameId = window.requestAnimationFrame(loop);
      }
    }

    const observer = new ResizeObserver(() => draw(performance.now()));
    observer.observe(activeShell);

    if (reducedMotion) {
      draw(performance.now());
    } else {
      frameId = window.requestAnimationFrame(loop);
    }

    return () => {
      observer.disconnect();
      window.cancelAnimationFrame(frameId);
    };
  }, [field, reducedMotion]);

  return (
    <div className="genesis-life-preview" ref={shellRef}>
      <canvas
        aria-label="Animated preview of Alpha's automatic Genesis seed becoming regions and species"
        className="genesis-life-canvas"
        ref={canvasRef}
        role="img"
      />
      <div className="genesis-life-readout" aria-hidden="true">
        <span>Automatic seed</span>
        <span>20 regions</span>
        <span>4 species pulses</span>
      </div>
    </div>
  );
}

function buildGenesisField() {
  const random = seededRandom(13931);
  const agents: GenesisAgent[] = Array.from({ length: 132 }, (_, index) => {
    const speciesBand = index % 4;
    return {
      x: random(),
      y: random(),
      radius: 1.4 + random() * 2.8,
      hue: [142, 192, 37, 213][speciesBand] + random() * 10,
      phase: random() * Math.PI * 2,
      speed: 0.45 + random() * 0.75,
      drift: 0.012 + random() * 0.026
    };
  });
  const resources: GenesisResource[] = Array.from({ length: 9 }, () => ({
    x: random(),
    y: random(),
    radius: 0.08 + random() * 0.1,
    phase: random() * Math.PI * 2
  }));

  return { agents, resources };
}

function drawGenesisFrame({
  context,
  field,
  height,
  reducedMotion,
  timestamp,
  width
}: {
  context: CanvasRenderingContext2D;
  field: ReturnType<typeof buildGenesisField>;
  height: number;
  reducedMotion: boolean;
  timestamp: number;
  width: number;
}) {
  const time = reducedMotion ? 0 : timestamp / 1000;
  const padding = 18;
  const contentWidth = width - padding * 2;
  const contentHeight = height - padding * 2;
  const cellGap = 5;
  const cellWidth = (contentWidth - cellGap * (grid.columns - 1)) / grid.columns;
  const cellHeight = (contentHeight - cellGap * (grid.rows - 1)) / grid.rows;

  context.clearRect(0, 0, width, height);
  context.fillStyle = "#fffdf8";
  context.fillRect(0, 0, width, height);

  const gradient = context.createLinearGradient(0, 0, width, height);
  gradient.addColorStop(0, "rgba(60, 140, 102, 0.08)");
  gradient.addColorStop(0.46, "rgba(27, 135, 165, 0.08)");
  gradient.addColorStop(1, "rgba(198, 132, 34, 0.1)");
  context.fillStyle = gradient;
  context.fillRect(0, 0, width, height);

  for (let row = 0; row < grid.rows; row += 1) {
    for (let column = 0; column < grid.columns; column += 1) {
      const index = row * grid.columns + column;
      const x = padding + column * (cellWidth + cellGap);
      const y = padding + row * (cellHeight + cellGap);
      const pulse = 0.5 + Math.sin(time * 0.75 + index * 0.72) * 0.5;
      const hue = 138 + ((index * 17) % 85);

      context.fillStyle = `hsla(${hue}, 38%, ${88 - pulse * 8}%, 0.78)`;
      context.strokeStyle = `rgba(24, 33, 31, ${0.09 + pulse * 0.08})`;
      context.lineWidth = 1;
      context.fillRect(x, y, cellWidth, cellHeight);
      context.strokeRect(x + 0.5, y + 0.5, cellWidth - 1, cellHeight - 1);

      drawMicroLattice(context, x, y, cellWidth, cellHeight, pulse);
    }
  }

  drawSeedWave(context, width, height, time);
  drawResources(context, field.resources, padding, contentWidth, contentHeight, time);
  drawAgents(context, field.agents, padding, contentWidth, contentHeight, time);
  drawEventThreads(context, field.agents.slice(0, 18), padding, contentWidth, contentHeight, time);
}

function drawMicroLattice(
  context: CanvasRenderingContext2D,
  x: number,
  y: number,
  width: number,
  height: number,
  pulse: number
) {
  const columns = 4;
  const rows = 3;
  context.strokeStyle = `rgba(24, 33, 31, ${0.035 + pulse * 0.035})`;
  context.lineWidth = 1;

  for (let column = 1; column < columns; column += 1) {
    const lineX = x + (width / columns) * column;
    context.beginPath();
    context.moveTo(lineX, y + 5);
    context.lineTo(lineX, y + height - 5);
    context.stroke();
  }

  for (let row = 1; row < rows; row += 1) {
    const lineY = y + (height / rows) * row;
    context.beginPath();
    context.moveTo(x + 5, lineY);
    context.lineTo(x + width - 5, lineY);
    context.stroke();
  }
}

function drawSeedWave(context: CanvasRenderingContext2D, width: number, height: number, time: number) {
  const centerX = width * 0.5;
  const centerY = height * 0.52;
  const pulse = 0.5 + Math.sin(time * 1.35) * 0.5;

  for (let index = 0; index < 3; index += 1) {
    context.beginPath();
    context.arc(centerX, centerY, 28 + index * 36 + pulse * 8, 0, Math.PI * 2);
    context.strokeStyle = `rgba(49, 95, 155, ${0.16 - index * 0.036})`;
    context.lineWidth = 1.4;
    context.stroke();
  }

  context.beginPath();
  context.arc(centerX, centerY, 9 + pulse * 4, 0, Math.PI * 2);
  context.fillStyle = "rgba(24, 33, 31, 0.88)";
  context.fill();
}

function drawResources(
  context: CanvasRenderingContext2D,
  resources: GenesisResource[],
  padding: number,
  width: number,
  height: number,
  time: number
) {
  for (const resource of resources) {
    const pulse = 0.5 + Math.sin(time * 0.9 + resource.phase) * 0.5;
    const x = padding + resource.x * width;
    const y = padding + resource.y * height;
    const radius = resource.radius * Math.min(width, height) * (0.72 + pulse * 0.4);

    context.beginPath();
    context.arc(x, y, radius, 0, Math.PI * 2);
    context.fillStyle = `rgba(198, 138, 36, ${0.06 + pulse * 0.06})`;
    context.fill();
  }
}

function drawAgents(
  context: CanvasRenderingContext2D,
  agents: GenesisAgent[],
  padding: number,
  width: number,
  height: number,
  time: number
) {
  for (const agent of agents) {
    const orbit = Math.sin(time * agent.speed + agent.phase);
    const sway = Math.cos(time * (agent.speed * 0.82) + agent.phase);
    const x = padding + clamp(agent.x + orbit * agent.drift) * width;
    const y = padding + clamp(agent.y + sway * agent.drift) * height;
    const glow = 0.55 + Math.sin(time * 1.2 + agent.phase) * 0.28;

    context.beginPath();
    context.arc(x, y, agent.radius * (0.82 + glow * 0.36), 0, Math.PI * 2);
    context.fillStyle = `hsla(${agent.hue}, 58%, 42%, ${0.35 + glow * 0.28})`;
    context.fill();
  }
}

function drawEventThreads(
  context: CanvasRenderingContext2D,
  agents: GenesisAgent[],
  padding: number,
  width: number,
  height: number,
  time: number
) {
  const centerX = padding + width * 0.5;
  const centerY = padding + height * 0.52;

  for (const [index, agent] of agents.entries()) {
    const orbit = Math.sin(time * agent.speed + agent.phase);
    const sway = Math.cos(time * (agent.speed * 0.82) + agent.phase);
    const x = padding + clamp(agent.x + orbit * agent.drift) * width;
    const y = padding + clamp(agent.y + sway * agent.drift) * height;
    const alpha = 0.05 + Math.max(0, Math.sin(time * 0.55 + index * 0.4)) * 0.12;

    context.beginPath();
    context.moveTo(centerX, centerY);
    context.lineTo(x, y);
    context.strokeStyle = `rgba(49, 95, 155, ${alpha})`;
    context.lineWidth = 1;
    context.stroke();
  }
}

function seededRandom(seed: number) {
  let state = seed || 1;
  return () => {
    state = (state * 1664525 + 1013904223) >>> 0;
    return state / 4294967296;
  };
}

function clamp(value: number) {
  return Math.max(0.02, Math.min(0.98, value));
}
