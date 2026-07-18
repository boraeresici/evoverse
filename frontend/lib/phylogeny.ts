import type { SpeciesSummary } from "./types";

export type PhyloNode = {
  species: SpeciesSummary;
  parentId: string | null;
  row: number;
  startAge: number;
  endAge: number;
  extinct: boolean;
  extinctLeaf: boolean;
  isCurrent: boolean;
  isAncestor: boolean;
  hasChildrenInSet: boolean;
};

export type PhyloTree = {
  nodes: PhyloNode[];
  minAge: number;
  maxAge: number;
  rows: number;
  currentId: string;
  totalSpecies: number;
  shownSpecies: number;
};

const MAX_DESCENDANTS = 40;
const MAX_SIBLINGS = 8;
// Extinct leaves have no recorded death age; give them a short visible stub.
const EXTINCT_LEAF_STUB = 0.06;

export function buildPhylogeny(
  current: SpeciesSummary,
  allSpecies: SpeciesSummary[],
  nowAge: number
): PhyloTree {
  const byId = new Map(allSpecies.map((item) => [item.id, item]));
  const childrenByParent = new Map<string, SpeciesSummary[]>();
  for (const species of allSpecies) {
    if (species.parentSpeciesId) {
      const list = childrenByParent.get(species.parentSpeciesId) ?? [];
      list.push(species);
      childrenByParent.set(species.parentSpeciesId, list);
    }
  }

  const included = new Map<string, SpeciesSummary>();
  const ancestorIds = new Set<string>();

  // 1. Ancestor chain (root -> current).
  const seenAncestor = new Set<string>();
  let cursor: SpeciesSummary | undefined = current;
  while (cursor) {
    included.set(cursor.id, cursor);
    const parentId = cursor.parentSpeciesId;
    if (!parentId || seenAncestor.has(parentId)) {
      break;
    }
    seenAncestor.add(parentId);
    const parent = byId.get(parentId);
    if (parent) {
      ancestorIds.add(parent.id);
    }
    cursor = parent;
  }

  // 2. Siblings (radiation around the current generation).
  if (current.parentSpeciesId) {
    const siblings = (childrenByParent.get(current.parentSpeciesId) ?? []).filter(
      (item) => item.id !== current.id
    );
    for (const sibling of siblings.slice(0, MAX_SIBLINGS)) {
      included.set(sibling.id, sibling);
    }
  }

  // 3. Descendants of the current species (bounded BFS).
  const queue: SpeciesSummary[] = [current];
  let descendantCount = 0;
  const visited = new Set<string>([current.id]);
  while (queue.length && descendantCount < MAX_DESCENDANTS) {
    const node = queue.shift() as SpeciesSummary;
    const kids = childrenByParent.get(node.id) ?? [];
    for (const kid of kids) {
      if (visited.has(kid.id)) {
        continue;
      }
      visited.add(kid.id);
      included.set(kid.id, kid);
      descendantCount += 1;
      queue.push(kid);
      if (descendantCount >= MAX_DESCENDANTS) {
        break;
      }
    }
  }

  const childrenInSet = new Map<string, SpeciesSummary[]>();
  for (const species of included.values()) {
    const parentId = species.parentSpeciesId;
    if (parentId && included.has(parentId)) {
      const list = childrenInSet.get(parentId) ?? [];
      list.push(species);
      childrenInSet.set(parentId, list);
    }
  }
  for (const list of childrenInSet.values()) {
    list.sort((a, b) => a.emergedAtWorldAge - b.emergedAtWorldAge || a.id.localeCompare(b.id));
  }

  const roots = [...included.values()].filter(
    (species) => !species.parentSpeciesId || !included.has(species.parentSpeciesId)
  );
  roots.sort((a, b) => a.emergedAtWorldAge - b.emergedAtWorldAge);

  // Tidy layout: leaves take sequential rows, a parent centres on its children.
  // This keeps the tree compact and balanced around the lineage rather than
  // staircasing every node onto its own row (which made deep trees enormous and
  // skewed the whole thing downward). A single-child chain collapses onto one row
  // — correct, it *is* one lineage advancing through time — so the label pass in
  // PhylogeneticTree spreads any labels that would collide, above vs below.
  const rowById = new Map<string, number>();
  let nextLeafRow = 0;
  const assign = (id: string): number => {
    const kids = childrenInSet.get(id) ?? [];
    if (kids.length === 0) {
      const row = nextLeafRow;
      nextLeafRow += 1;
      rowById.set(id, row);
      return row;
    }
    const kidRows = kids.map((kid) => assign(kid.id));
    const row = (Math.min(...kidRows) + Math.max(...kidRows)) / 2;
    rowById.set(id, row);
    return row;
  };
  for (const root of roots) {
    assign(root.id);
  }

  const ages = [...included.values()].map((item) => item.emergedAtWorldAge);
  const minAge = Math.min(...ages);
  const maxAge = Math.max(nowAge, ...ages);
  const ageSpan = maxAge - minAge || 1;

  const nodes: PhyloNode[] = [...included.values()].map((species) => {
    const kids = childrenInSet.get(species.id) ?? [];
    const extinct = species.status === "extinct";
    const lastChildAge = kids.length ? Math.max(...kids.map((k) => k.emergedAtWorldAge)) : null;
    let endAge: number;
    let extinctLeaf = false;
    if (extinct) {
      endAge = lastChildAge ?? species.emergedAtWorldAge + ageSpan * EXTINCT_LEAF_STUB;
      extinctLeaf = lastChildAge === null;
    } else {
      endAge = Math.max(lastChildAge ?? species.emergedAtWorldAge, maxAge);
    }
    return {
      species,
      parentId: species.parentSpeciesId,
      row: rowById.get(species.id) ?? 0,
      startAge: species.emergedAtWorldAge,
      endAge,
      extinct,
      extinctLeaf,
      isCurrent: species.id === current.id,
      isAncestor: ancestorIds.has(species.id),
      hasChildrenInSet: kids.length > 0
    };
  });

  return {
    nodes,
    minAge,
    maxAge,
    rows: Math.max(1, nextLeafRow),
    currentId: current.id,
    totalSpecies: allSpecies.length,
    shownSpecies: included.size
  };
}
