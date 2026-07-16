import { describe, expect, it } from "vitest";

import { lensRng } from "./lensRng";
import {
  deriveBodyParams,
  deriveFormState,
  resolveLensMode
} from "./organismLens";
import type { RegionSummary, SpeciesSummary } from "./types";

function makeSpecies(overrides: Partial<SpeciesSummary> = {}): SpeciesSummary {
  return {
    id: "sp-0007",
    name: "Solen",
    status: "stable",
    population: 12000,
    originRegionId: "region-087",
    emergedAtWorldAge: 3979,
    generation: 1,
    parentSpeciesId: null,
    chirality: -1,
    heterochiralLoad: 0,
    traits: {
      efficiency: 0.69,
      adaptation: 0.68,
      cooperation: 0.62,
      mobility: 0.35,
      resilience: 0.69
    },
    regions: [],
    forecast: {
      extinctionRisk: 0.4,
      dominanceProbability: 0.4,
      expansionPressure: 0.3,
      mutationVolatility: 0.3
    },
    ...overrides
  };
}

function makeRegion(overrides: Partial<RegionSummary> = {}): RegionSummary {
  return {
    id: "region-087",
    x: 3,
    y: 5,
    biomeType: "temperate",
    energyLevel: 0.5,
    resourceDensity: 0.5,
    stability: 0.6,
    lifeIndex: 0.4,
    chiralityEe: -1,
    chiralityLocked: true,
    collapsed: false,
    dominantSpeciesId: "sp-0007",
    dominantSpeciesName: "Solen",
    population: 12000,
    ...overrides
  };
}

describe("lensRng", () => {
  it("is deterministic for the same key", () => {
    const a = lensRng("body", "sp-0007");
    const b = lensRng("body", "sp-0007");
    const drawsA = [a.next(), a.next(), a.next()];
    const drawsB = [b.next(), b.next(), b.next()];
    expect(drawsA).toEqual(drawsB);
  });

  it("scatters sibling keys rather than clustering them", () => {
    // Guards the keying, not the algorithm: this passes for any decent hash, and
    // is here to catch a stream that stops depending on the lineage id at all —
    // e.g. a future refactor keying only on generation, which would hand every
    // sibling the same body.
    const firstDraws = Array.from({ length: 20 }, (_, index) =>
      lensRng("body", `sp-${String(index).padStart(4, "0")}`).next()
    );
    const spread = Math.max(...firstDraws) - Math.min(...firstDraws);
    expect(spread).toBeGreaterThan(0.6);

    // And no two of them collide.
    expect(new Set(firstDraws).size).toBe(firstDraws.length);
  });

  it("stays inside [0, 1) across many draws", () => {
    const rng = lensRng("spread", "check");
    for (let i = 0; i < 5000; i += 1) {
      const value = rng.next();
      expect(value).toBeGreaterThanOrEqual(0);
      expect(value).toBeLessThan(1);
    }
  });

  it("spreads roughly uniformly", () => {
    const rng = lensRng("uniform", "check");
    const buckets = new Array(10).fill(0);
    for (let i = 0; i < 10000; i += 1) {
      buckets[Math.floor(rng.next() * 10)] += 1;
    }
    for (const count of buckets) {
      expect(count).toBeGreaterThan(700);
      expect(count).toBeLessThan(1300);
    }
  });

  it("honours range and int bounds", () => {
    const rng = lensRng("bounds");
    for (let i = 0; i < 1000; i += 1) {
      const r = rng.range(-2, 5);
      expect(r).toBeGreaterThanOrEqual(-2);
      expect(r).toBeLessThan(5);
      const n = rng.int(1, 6);
      expect(Number.isInteger(n)).toBe(true);
      expect(n).toBeGreaterThanOrEqual(1);
      expect(n).toBeLessThanOrEqual(6);
    }
  });

  it("refuses to pick from an empty list", () => {
    expect(() => lensRng("pick").pick([])).toThrow();
  });
});

describe("resolveLensMode", () => {
  it("unlocks the form for a stable lineage in a locked region", () => {
    const state = resolveLensMode({ species: makeSpecies(), originRegion: makeRegion() });
    expect(state.mode).toBe("form");
  });

  it("unlocks the form for a dominant lineage", () => {
    const state = resolveLensMode({
      species: makeSpecies({ status: "dominant" }),
      originRegion: makeRegion()
    });
    expect(state.mode).toBe("form");
  });

  it("stays locked while the origin region is racemic", () => {
    const state = resolveLensMode({
      species: makeSpecies(),
      originRegion: makeRegion({ chiralityLocked: false, chiralityEe: 0.2 })
    });
    expect(state.mode).toBe("locked");
    expect(state.reason).toMatch(/racemic/i);
  });

  it.each(["emerging", "declining", "extinct"])("stays locked for a %s lineage", (status) => {
    const state = resolveLensMode({
      species: makeSpecies({ status }),
      originRegion: makeRegion()
    });
    expect(state.mode).toBe("locked");
  });

  it("stays locked when the origin region is unavailable", () => {
    const state = resolveLensMode({ species: makeSpecies(), originRegion: null });
    expect(state.mode).toBe("locked");
  });

  it("never returns mind until T2 ships mind_locked", () => {
    // Guards the seam: the member exists for the renderer, but nothing can
    // reach it yet. This test should be rewritten — not deleted — by §6.5.
    const state = resolveLensMode({
      species: makeSpecies({ status: "dominant" }),
      originRegion: makeRegion()
    });
    expect(state.mode).not.toBe("mind");
  });
});

describe("deriveBodyParams", () => {
  it("is deterministic for the same species", () => {
    expect(deriveBodyParams(makeSpecies())).toEqual(deriveBodyParams(makeSpecies()));
  });

  it("gives sibling lineages visibly different bodies", () => {
    const a = deriveBodyParams(makeSpecies({ id: "sp-0007" }));
    const b = deriveBodyParams(makeSpecies({ id: "sp-0008" }));
    expect(a).not.toEqual(b);
  });

  it("reads the hand into the coil direction", () => {
    expect(deriveBodyParams(makeSpecies({ chirality: -1 })).coilDirection).toBe(-1);
    expect(deriveBodyParams(makeSpecies({ chirality: 1 })).coilDirection).toBe(1);
    expect(deriveBodyParams(makeSpecies({ chirality: 0 })).coilDirection).toBe(0);
  });

  it("ignores per-tick state so the body does not re-roll while observed", () => {
    // heterochiralLoad and population move every tick; geometry must not.
    const before = deriveBodyParams(makeSpecies({ heterochiralLoad: 0, population: 12000 }));
    const after = deriveBodyParams(makeSpecies({ heterochiralLoad: 0.6, population: 400 }));
    expect(after).toEqual(before);
  });

  it("lets traits steer the body", () => {
    const nimble = deriveBodyParams(makeSpecies({ traits: { ...makeSpecies().traits, mobility: 1 } }));
    const sessile = deriveBodyParams(makeSpecies({ traits: { ...makeSpecies().traits, mobility: 0 } }));
    expect(nimble.limbs).toBeGreaterThan(sessile.limbs);
  });

  it("keeps every parameter inside its stated bounds", () => {
    for (let i = 0; i < 200; i += 1) {
      const params = deriveBodyParams(makeSpecies({ id: `sp-${i}`, generation: i % 5 }));
      expect(params.segments).toBeGreaterThan(0);
      expect(params.limbs % 2).toBe(0);
      for (const key of ["radius", "taper", "limbLength", "symmetry"] as const) {
        expect(params[key]).toBeGreaterThanOrEqual(0);
        expect(params[key]).toBeLessThanOrEqual(1);
      }
    }
  });

  it("survives a species with no traits", () => {
    expect(() => deriveBodyParams(makeSpecies({ traits: {} }))).not.toThrow();
  });
});

describe("deriveFormState", () => {
  it("reads a clean lineage as fully coherent", () => {
    const state = deriveFormState(makeSpecies({ heterochiralLoad: 0 }));
    expect(state.coherence).toBe(1);
    expect(state.counterTwist).toBe(0);
    expect(state.failing).toBe(false);
  });

  it("turns load into counter-twist", () => {
    const state = deriveFormState(makeSpecies({ heterochiralLoad: 0.4 }));
    expect(state.coherence).toBeCloseTo(0.6);
    expect(state.counterTwist).toBeCloseTo(0.4);
    expect(state.failing).toBe(false);
  });

  it("flags a lethal load as a failing form", () => {
    expect(deriveFormState(makeSpecies({ heterochiralLoad: 0.85 })).failing).toBe(true);
    expect(deriveFormState(makeSpecies({ heterochiralLoad: 0.9 })).failing).toBe(true);
  });

  it("clamps loads outside 0..1", () => {
    expect(deriveFormState(makeSpecies({ heterochiralLoad: 1.4 })).coherence).toBe(0);
    expect(deriveFormState(makeSpecies({ heterochiralLoad: -0.2 })).coherence).toBe(1);
  });

  it("never lets load invert the coil, at any load", () => {
    // The hand is one-way (§6.2). A non-positive slack would mirror the helix
    // and render a left-handed lineage as right-handed — the Lens contradicting
    // the single fact it exists to show. This held for load <= 0.625 by luck;
    // it must hold everywhere.
    for (let load = 0; load <= 1.5; load += 0.01) {
      const state = deriveFormState(makeSpecies({ heterochiralLoad: load }));
      expect(state.coilSlack).toBeGreaterThan(0);
    }
  });

  it("slackens the coil as load rises, without reversing it", () => {
    const clean = deriveFormState(makeSpecies({ heterochiralLoad: 0 }));
    const strained = deriveFormState(makeSpecies({ heterochiralLoad: 0.4 }));
    const lethal = deriveFormState(makeSpecies({ heterochiralLoad: 1 }));
    expect(clean.coilSlack).toBe(1);
    expect(strained.coilSlack).toBeLessThan(clean.coilSlack);
    expect(lethal.coilSlack).toBeLessThan(strained.coilSlack);
    expect(lethal.coilSlack).toBeGreaterThan(0);
  });
});
