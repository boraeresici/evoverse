/**
 * Organism Lens — pure core.
 *
 * Decides whether a lineage's form can be inspected, and derives that form
 * deterministically from species state. No rendering, no three.js: this module
 * is the model the Lens draws, and it stays testable on its own.
 *
 * Design spec: docs/CHIRALITY_AND_MIND.md §8 (visualization hooks) and §6.2–6.3
 * (the hand a lineage carries, and the load a mismatched one bears).
 */

import { lensRng } from "./lensRng";
import type { RegionSummary, SpeciesSummary } from "./types";

/**
 * `locked` — no stable form to inspect yet (2D sprite only).
 * `form`   — the organism's body, generated from species state.
 * `mind`   — T2: the lineage's internal world-model beside reality.
 *
 * `mind` is unreachable today by design: it needs `mind_locked`, which the
 * cognitive tier (§6.5) has yet to set and the API has yet to serve. The member
 * exists so the renderer's switch is written for it now rather than reshaped
 * later — see `resolveLensMode`.
 */
export type LensMode = "locked" | "form" | "mind";

export type LensState = {
  mode: LensMode;
  /** Why this mode — surfaced as the "locked" affordance's tooltip. */
  reason: string;
};

/** Only a lineage that holds its ground has a form worth resolving. */
const INSPECTABLE_STATUSES: ReadonlySet<string> = new Set(["stable", "dominant"]);

/**
 * The hand a region may be *shown* to carry: 0 until it latches, then the sign
 * of its excess. Not the same as `Math.sign(chiralityEe)` — a drifting region
 * has a momentary excess that means nothing yet, and §8 is explicit that a
 * racemic region has no hand to display. Both the micro field and the Lens gate
 * on this, so they never disagree about whether a hand exists.
 */
export function regionHandSign(
  region: Pick<RegionSummary, "chiralityEe" | "chiralityLocked">
): number {
  if (!region.chiralityLocked) {
    return 0;
  }
  return Math.sign(region.chiralityEe);
}

/**
 * §8's gate. Note what is *not* consulted: the universe's homochirality index.
 * A locked region already implies |ee| = 1 there, so the region's own lock is
 * the operative condition, and the frontend avoids duplicating
 * `life_gate_index` — a hot-editable backend rule that would silently drift
 * from any copy kept here.
 */
export function resolveLensMode({
  species,
  originRegion
}: {
  species: SpeciesSummary;
  originRegion: RegionSummary | null;
}): LensState {
  if (!originRegion) {
    return { mode: "locked", reason: "This lineage's origin region is unavailable." };
  }
  if (!originRegion.chiralityLocked) {
    return {
      mode: "locked",
      reason: "The origin region is still racemic — no stable form has settled."
    };
  }
  if (!INSPECTABLE_STATUSES.has(species.status)) {
    return {
      mode: "locked",
      reason: `A ${species.status} lineage holds no form steady enough to inspect.`
    };
  }
  // T2 seam: once the cognitive tier sets `mind_locked` and the API serves it,
  // a mind-locked lineage resolves to "mind" here.
  return { mode: "form", reason: "This lineage carries one hand and holds its form." };
}

/**
 * The organism's skeleton. Derived only from state that is fixed for a species'
 * lifetime — `id`, `generation`, `traits`, and the hand it committed to — so the
 * body is stable across ticks and can be built once and cached. Anything that
 * moves tick to tick belongs in `deriveFormState`, never here: rebuilding
 * geometry on every poll would re-roll the creature while you watch it.
 */
export type BodyParams = {
  /** Vertebrae along the spine. */
  segments: number;
  /** Coil handedness: +1 right, -1 left, 0 for an uncommitted lineage. */
  coilDirection: number;
  /** Helical turns along the body — the hand made visible. */
  coilTurns: number;
  /** Core thickness at the widest point, 0..1. */
  radius: number;
  /** How sharply the body narrows toward the tail, 0..1. */
  taper: number;
  /** Paired appendages. */
  limbs: number;
  /** Appendage reach relative to the core, 0..1. */
  limbLength: number;
  /** Bilateral regularity, 0..1 — low is a lopsided body. */
  symmetry: number;
  /** Surface ridges per segment. */
  ridges: number;
};

const clamp01 = (value: number) => Math.min(1, Math.max(0, value));

function trait(species: SpeciesSummary, name: string): number {
  return clamp01(Number(species.traits?.[name] ?? 0.5));
}

/**
 * Traits steer the body; the RNG only breaks ties, so two lineages with similar
 * traits still read as different creatures without the traits ceasing to mean
 * anything.
 */
export function deriveBodyParams(species: SpeciesSummary): BodyParams {
  const rng = lensRng("body", species.id, species.generation);

  const efficiency = trait(species, "efficiency");
  const adaptation = trait(species, "adaptation");
  const cooperation = trait(species, "cooperation");
  const mobility = trait(species, "mobility");
  const resilience = trait(species, "resilience");

  return {
    // A resilient lineage is built of more, sturdier segments.
    segments: Math.round(6 + resilience * 10 + rng.range(-1, 1)),
    coilDirection: Math.sign(species.chirality),
    // An efficient body packs more turns into the same length.
    coilTurns: Number((1.5 + efficiency * 4 + rng.range(-0.3, 0.3)).toFixed(3)),
    radius: Number(clamp01(0.25 + adaptation * 0.5 + rng.range(-0.05, 0.05)).toFixed(3)),
    taper: Number(clamp01(0.2 + mobility * 0.6 + rng.range(-0.05, 0.05)).toFixed(3)),
    // Mobility buys appendages, in pairs.
    limbs: Math.round(mobility * 4 + rng.range(0, 1)) * 2,
    limbLength: Number(clamp01(0.2 + mobility * 0.7 + rng.range(-0.05, 0.05)).toFixed(3)),
    // Cooperative lineages grow orderly, bilateral bodies.
    symmetry: Number(clamp01(0.45 + cooperation * 0.5 + rng.range(-0.04, 0.04)).toFixed(3)),
    ridges: Math.round(1 + resilience * 5 + rng.range(0, 1))
  };
}

/**
 * The part of the form that breathes with the simulation. Recomputed per tick
 * from `heterochiralLoad` and applied as a continuous modifier over the cached
 * geometry — a mismatched lineage should visibly fight its own shape (§6.3).
 */
export type FormState = {
  /** 0..1 — how cleanly the lineage carries one hand (the species-scope maturity metric, §4). */
  coherence: number;
  /** 0..1 — twist opposing the body's own coil; a lineage at odds with its region. */
  counterTwist: number;
  /**
   * Multiplier on the coil under load, in (0, 1]. Strictly positive: load
   * slackens a lineage's coil, but must never invert it. A lineage's hand is
   * one-way (§6.2) — it is inherited and never re-derived — so a coil that
   * reversed under strain would render a left-handed lineage as right-handed
   * and contradict the one thing the Lens exists to show.
   */
  coilSlack: number;
  /** 0..1 — restlessness in the surface. */
  jitter: number;
  /** True once the load is lethal (§6.3): the form is coming apart, not merely strained. */
  failing: boolean;
};

/** The tightest a fully-loaded coil may wind down to — never 0, never negative. */
const MIN_COIL_SLACK = 0.15;

/**
 * Mirrors `heterochiral_lethal_load` in `ChiralityRules`. Duplicated here only
 * as a *visual* threshold — it changes nothing in the simulation, and the engine
 * remains the sole authority on what actually kills a population.
 */
const LETHAL_LOAD = 0.85;

export function deriveFormState(species: SpeciesSummary): FormState {
  const load = clamp01(Number(species.heterochiralLoad ?? 0));
  return {
    coherence: Number((1 - load).toFixed(3)),
    counterTwist: Number(load.toFixed(3)),
    coilSlack: Number(Math.max(MIN_COIL_SLACK, 1 - load * 1.6).toFixed(3)),
    jitter: Number((load * load).toFixed(3)),
    failing: load >= LETHAL_LOAD
  };
}
