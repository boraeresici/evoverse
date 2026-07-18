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
  // Compact layouts let a single-child chain share one row, so two labels can land
  // at the same height. Decide per node whether its label sits above or below the
  // lifeline so none overlap — the layout stays tight, the text stays legible.
  const labelSides = resolveLabelSides(tree.nodes, xOf, yOf);

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
            labelBelow={labelSides.get(node.species.id) === "below"}
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
  labelBelow,
  onOpen
}: {
  node: PhyloNode;
  x: number;
  y: number;
  labelBelow: boolean;
  onOpen?: () => void;
}) {
  const nearRight = x > VIEW_W - RIGHT_PAD;
  const labelX = nearRight ? x - 10 : x + 10;
  const anchor = nearRight ? "end" : "start";
  // A single line per node (name + generation), so a label needs only one side of
  // the lifeline — which is what lets above/below placement separate collisions.
  const labelY = labelBelow ? y + 16 : y - 9;
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

/**
 * Greedy above/below assignment so no two node labels overlap. Nodes are placed
 * left-to-right; each label prefers the space above its lifeline and drops below
 * only if that would collide with one already placed. A label is one text line, so
 * a node occupies just one side — leaving the other free for a same-row neighbour.
 */
function resolveLabelSides(
  nodes: PhyloNode[],
  xOf: (age: number) => number,
  yOf: (row: number) => number
): Map<string, "above" | "below"> {
  const CHAR_W = 6.6;
  const GAP = 6;
  const LABEL_H = 15;
  const placed: Array<{ x0: number; x1: number; y0: number; y1: number }> = [];
  const sides = new Map<string, "above" | "below">();
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
    const box = (top: number) => ({ x0, x1, y0: top, y1: top + LABEL_H });
    const above = box(y - 9 - LABEL_H);
    const below = box(y + 6);
    const hits = (b: { x0: number; x1: number; y0: number; y1: number }) =>
      placed.some(
        (p) => b.x0 < p.x1 + GAP && b.x1 + GAP > p.x0 && b.y0 < p.y1 && b.y1 > p.y0
      );
    const side = !hits(above) ? "above" : !hits(below) ? "below" : "above";
    sides.set(node.species.id, side);
    placed.push(side === "above" ? above : below);
  }
  return sides;
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
