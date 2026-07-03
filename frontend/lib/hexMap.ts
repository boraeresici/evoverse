import type { ChronicleEvent, RegionSummary } from "./types";

export type HexCell = {
  region: RegionSummary;
  leftPct: number;
  topPct: number;
  widthPct: number;
  heightPct: number;
};

export type HexLayout = {
  cells: HexCell[];
  aspectRatio: number;
  cols: number;
  rows: number;
};

// Pointy-top hexagon on an odd-r offset grid (odd rows shifted right).
const HEX_HEIGHT_RATIO = 1.1547; // 2 / sqrt(3): pointy-top height relative to width
const ROW_STEP_RATIO = 0.75; // vertical interlock

export function hexLayout(regions: RegionSummary[]): HexLayout {
  if (regions.length === 0) {
    return { cells: [], aspectRatio: 1, cols: 1, rows: 1 };
  }
  const cols = Math.max(...regions.map((r) => r.x)) + 1;
  const rows = Math.max(...regions.map((r) => r.y)) + 1;

  const w = 1 / (cols + 0.5); // cell width as a fraction of container width
  const hexH = w * HEX_HEIGHT_RATIO; // cell height as a fraction of container WIDTH
  const rowStep = hexH * ROW_STEP_RATIO;
  const totalH = (rows - 1) * rowStep + hexH; // total height as a fraction of container width

  const cells = regions.map((region) => {
    const leftFrac = (region.x + (region.y % 2 === 1 ? 0.5 : 0)) * w;
    const topFrac = region.y * rowStep;
    return {
      region,
      leftPct: leftFrac * 100,
      topPct: (topFrac / totalH) * 100,
      widthPct: w * 100,
      heightPct: (hexH / totalH) * 100
    };
  });

  return { cells, aspectRatio: 1 / totalH, cols, rows };
}

export function hexNeighbors(x: number, y: number): Array<{ x: number; y: number }> {
  const even = y % 2 === 0;
  return [
    { x: x + 1, y },
    { x: x - 1, y },
    { x: even ? x - 1 : x, y: y - 1 },
    { x: even ? x : x + 1, y: y - 1 },
    { x: even ? x - 1 : x, y: y + 1 },
    { x: even ? x : x + 1, y: y + 1 }
  ];
}

/**
 * Multi-source BFS ring distance from every region with a recent event to its
 * spatial neighbours, so activity visibly ripples outward across the hex field.
 * Returns regionId -> ring (0 = event origin) for cells within `maxRing`.
 */
export function eventWaveRings(
  regions: RegionSummary[],
  events: ChronicleEvent[],
  maxRing = 2
): Map<string, number> {
  const byCoord = new Map<string, RegionSummary>();
  for (const region of regions) {
    byCoord.set(coordKey(region.x, region.y), region);
  }

  const rings = new Map<string, number>();
  const queue: Array<{ region: RegionSummary; ring: number }> = [];
  const seenOrigins = new Set<string>();
  for (const event of events) {
    if (!event.regionId || seenOrigins.has(event.regionId)) {
      continue;
    }
    seenOrigins.add(event.regionId);
    const region = regions.find((r) => r.id === event.regionId);
    if (region) {
      rings.set(region.id, 0);
      queue.push({ region, ring: 0 });
    }
  }

  while (queue.length) {
    const { region, ring } = queue.shift() as { region: RegionSummary; ring: number };
    if (ring >= maxRing) {
      continue;
    }
    for (const neighbor of hexNeighbors(region.x, region.y)) {
      const next = byCoord.get(coordKey(neighbor.x, neighbor.y));
      if (!next) {
        continue;
      }
      const nextRing = ring + 1;
      const existing = rings.get(next.id);
      if (existing === undefined || nextRing < existing) {
        rings.set(next.id, nextRing);
        queue.push({ region: next, ring: nextRing });
      }
    }
  }

  return rings;
}

function coordKey(x: number, y: number): string {
  return `${x},${y}`;
}
