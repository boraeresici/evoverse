"use client";

import { useRouter } from "next/navigation";
import { useMemo } from "react";
import { buildPhylogeny, type PhyloNode } from "@/lib/phylogeny";
import type { SpeciesSummary } from "@/lib/types";

type PhylogeneticTreeProps = {
  current: SpeciesSummary;
  allSpecies: SpeciesSummary[];
  nowAge: number;
  majorMutationAges: number[];
};

const ROW_HEIGHT = 46;
const TOP_PAD = 20;
const BOTTOM_PAD = 40;
const LEFT_PAD = 18;
const RIGHT_PAD = 150;
const VIEW_W = 760;

export function PhylogeneticTree({
  current,
  allSpecies,
  nowAge,
  majorMutationAges
}: PhylogeneticTreeProps) {
  const router = useRouter();
  const tree = useMemo(
    () => buildPhylogeny(current, allSpecies, nowAge),
    [current, allSpecies, nowAge]
  );

  const rowById = new Map(tree.nodes.map((node) => [node.species.id, node.row]));
  const height = TOP_PAD + tree.rows * ROW_HEIGHT + BOTTOM_PAD;
  const plotW = VIEW_W - LEFT_PAD - RIGHT_PAD;
  const span = tree.maxAge - tree.minAge || 1;

  const xOf = (age: number) => LEFT_PAD + ((age - tree.minAge) / span) * plotW;
  const yOf = (row: number) => TOP_PAD + row * ROW_HEIGHT + ROW_HEIGHT / 2;

  const axisTicks = buildAxisTicks(tree.minAge, tree.maxAge);
  const currentNode = tree.nodes.find((node) => node.isCurrent) ?? null;
  // Compact layouts let a single-child chain share one row, so labels can pile onto
  // one height. Resolve a distinct baseline per label so none overlap — the layout
  // stays tight, the text stays legible.
  const labelOffsets = resolveLabelOffsets(tree.nodes, xOf, yOf);

  return (
    <div className="phylo-tree">
      <div className="phylo-legend" aria-hidden="true">
        <span className="phylo-key emergence">
          <i />
          Emergence
        </span>
        <span className="phylo-key mutation">
          <i />
          Major mutation
        </span>
        <span className="phylo-key extinction">
          <i />
          Extinction
        </span>
        <span className="phylo-key current">
          <i />
          Selected
        </span>
        <span className="phylo-shown">
          {tree.shownSpecies} of {tree.totalSpecies} species
        </span>
      </div>

      <svg
        className="phylo-svg"
        viewBox={`0 0 ${VIEW_W} ${height}`}
        role="group"
        aria-label={`Phylogenetic tree centered on ${current.name}`}
      >
        {/* Time axis */}
        {axisTicks.map((tick) => {
          const x = xOf(tick);
          return (
            <g className="phylo-axis" key={`axis-${tick}`}>
              <line x1={x} x2={x} y1={TOP_PAD - 6} y2={height - BOTTOM_PAD + 6} />
              <text x={x} y={height - BOTTOM_PAD + 22} textAnchor="middle">
                {tick.toLocaleString()}
              </text>
            </g>
          );
        })}
        <text className="phylo-axis-label" x={LEFT_PAD} y={height - 8}>
          Alpha Age →
        </text>

        {/* Branch connectors (parent row -> child row at child emergence age) */}
        {tree.nodes.map((node) => {
          if (!node.parentId || !rowById.has(node.parentId)) {
            return null;
          }
          const x = xOf(node.startAge);
          const y1 = yOf(rowById.get(node.parentId) as number);
          const y2 = yOf(node.row);
          return (
            <line
              className="phylo-branch"
              key={`branch-${node.species.id}`}
              x1={x}
              x2={x}
              y1={y1}
              y2={y2}
            />
          );
        })}

        {/* Lifelines */}
        {tree.nodes.map((node) => {
          const y = yOf(node.row);
          return (
            <line
              className={lifelineClass(node)}
              key={`life-${node.species.id}`}
              x1={xOf(node.startAge)}
              x2={xOf(node.endAge)}
              y1={y}
              y2={y}
            />
          );
        })}

        {/* Extinction caps */}
        {tree.nodes
          .filter((node) => node.extinct)
          .map((node) => {
            const x = xOf(node.endAge);
            const y = yOf(node.row);
            return (
              <g className="phylo-extinct-cap" key={`ext-${node.species.id}`}>
                <line x1={x - 4} x2={x + 4} y1={y - 5} y2={y + 5} />
                <line x1={x - 4} x2={x + 4} y1={y + 5} y2={y - 5} />
              </g>
            );
          })}

        {/* Major mutation markers on the current lineage */}
        {currentNode
          ? majorMutationAges
              .filter((age) => age >= currentNode.startAge && age <= currentNode.endAge)
              .map((age, index) => {
                const x = xOf(age);
                const y = yOf(currentNode.row);
                return (
                  <path
                    className="phylo-mutation"
                    key={`mut-${index}-${age}`}
                    d={`M${x} ${y - 6} L${x + 6} ${y} L${x} ${y + 6} L${x - 6} ${y} Z`}
                  />
                );
              })
          : null}

        {/* Nodes + labels */}
        {tree.nodes.map((node) => (
          <PhyloNodeMark
            key={node.species.id}
            node={node}
            x={xOf(node.startAge)}
            y={yOf(node.row)}
            labelY={labelOffsets.get(node.species.id) ?? yOf(node.row) - 9}
            onOpen={
              node.isCurrent ? undefined : () => router.push(`/species/${node.species.id}`)
            }
          />
        ))}
      </svg>
    </div>
  );
}

function PhyloNodeMark({
  node,
  x,
  y,
  labelY,
  onOpen
}: {
  node: PhyloNode;
  x: number;
  y: number;
  labelY: number;
  onOpen?: () => void;
}) {
  const nearRight = x > VIEW_W - RIGHT_PAD;
  const labelX = nearRight ? x - 10 : x + 10;
  const anchor = nearRight ? "end" : "start";
  const interactive = Boolean(onOpen);
  return (
    <g
      className={`phylo-node status-${node.species.status}${node.isCurrent ? " current" : ""}${
        interactive ? " interactive" : ""
      }`}
      role={interactive ? "link" : undefined}
      tabIndex={interactive ? 0 : undefined}
      aria-label={`${node.species.name}, generation ${node.species.generation}, ${node.species.status}, emerged at age ${node.startAge}`}
      onClick={onOpen}
      onKeyDown={(event) => {
        if (onOpen && (event.key === "Enter" || event.key === " ")) {
          event.preventDefault();
          onOpen();
        }
      }}
    >
      <title>{`${node.species.name} · Gen ${node.species.generation} · ${node.species.status} · Age ${node.startAge.toLocaleString()}`}</title>
      {node.isCurrent ? <circle className="phylo-halo" cx={x} cy={y} r={9} /> : null}
      <circle className="phylo-dot" cx={x} cy={y} r={node.isCurrent ? 6 : 4.5} />
      <text className="phylo-label" x={labelX} y={labelY} textAnchor={anchor}>
        {truncate(node.species.name, 16)}
        <tspan className="phylo-gen"> · G{node.species.generation}</tspan>
      </text>
    </g>
  );
}

// Text baselines to try per label, relative to the node's lifeline y: near above,
// near below, then progressively farther out on alternating sides. Two slots are
// not enough — a single-child chain (or several lineages emerging at nearly the
// same age) can pile many labels onto one x, and each needs its own height.
const LABEL_LEVELS = [-9, 16, -27, 34, -45, 52, -63, 70];

/**
 * Greedy label placement so no two node labels overlap. Nodes are laid out
 * left-to-right; each label takes the first candidate height (nearest the lifeline
 * first) whose box clears every label already placed. Returns the chosen text
 * baseline y per node.
 */
function resolveLabelOffsets(
  nodes: PhyloNode[],
  xOf: (age: number) => number,
  yOf: (row: number) => number
): Map<string, number> {
  const CHAR_W = 6.6;
  const GAP = 6;
  const LABEL_H = 15;
  const placed: Array<{ x0: number; x1: number; y0: number; y1: number }> = [];
  const offsets = new Map<string, number>();
  const ordered = [...nodes].sort((a, b) => xOf(a.startAge) - xOf(b.startAge));
  for (const node of ordered) {
    const x = xOf(node.startAge);
    const y = yOf(node.row);
    const nearRight = x > VIEW_W - RIGHT_PAD;
    const width =
      (Math.min(node.species.name.length, 16) + String(node.species.generation).length + 4) *
      CHAR_W;
    const x0 = nearRight ? x - 10 - width : x + 10;
    const x1 = nearRight ? x - 10 : x + 10 + width;
    const boxAt = (baseline: number) => ({ x0, x1, y0: baseline - LABEL_H + 2, y1: baseline + 3 });
    const hits = (b: { x0: number; x1: number; y0: number; y1: number }) =>
      placed.some(
        (p) => b.x0 < p.x1 + GAP && b.x1 + GAP > p.x0 && b.y0 < p.y1 && b.y1 > p.y0
      );
    let chosen = LABEL_LEVELS[0];
    for (const level of LABEL_LEVELS) {
      if (!hits(boxAt(y + level))) {
        chosen = level;
        break;
      }
      chosen = level; // fall through to the farthest if all collide
    }
    offsets.set(node.species.id, y + chosen);
    placed.push(boxAt(y + chosen));
  }
  return offsets;
}

function lifelineClass(node: PhyloNode): string {
  const base = `phylo-lifeline status-${node.species.status}`;
  if (node.isCurrent) {
    return `${base} current`;
  }
  if (node.extinct) {
    return `${base} extinct`;
  }
  return base;
}

function buildAxisTicks(minAge: number, maxAge: number): number[] {
  const span = maxAge - minAge;
  if (span <= 0) {
    return [minAge];
  }
  const target = 5;
  const rawStep = span / target;
  const magnitude = Math.pow(10, Math.floor(Math.log10(rawStep)));
  const niceStep = [1, 2, 5, 10].map((m) => m * magnitude).find((s) => s >= rawStep) ?? magnitude * 10;
  const ticks: number[] = [];
  const start = Math.ceil(minAge / niceStep) * niceStep;
  for (let value = start; value <= maxAge; value += niceStep) {
    ticks.push(Math.round(value));
  }
  if (ticks.length === 0) {
    ticks.push(minAge, maxAge);
  }
  return ticks;
}

function truncate(value: string, max: number): string {
  return value.length > max ? `${value.slice(0, max - 1)}…` : value;
}
