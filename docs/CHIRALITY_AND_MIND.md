# Evoverse — Chirality & Mind

> **Status:** partially implemented. **T1 (§11 steps 1–3) is built and tested**
> (`backend/tests/test_chirality.py`): the region/universe chirality field, the
> bifurcation + avalanche tick rule, `ChiralityRules`, and `homochirality_index`
> (step 1); one-way lineage inheritance, heterochiral selection, and the
> `SYMMETRY_BREAK` event (step 2); and the two-tier Era gate with the `ERA_ADVANCED`
> event (step 3). All surfaced on the API and persisted. The Organism Lens (step 4)
> and the cognitive tier / T2 (step 5) remain design-only — including the
> `Species.mind_locked` flag, which exists and gates Intelligence but is never set
> until T2. This document is the spec; each remaining slice ships only when wired
> in and tested.

This is a design spec, not an empirical claim about biology. Evoverse is an
observatory and a modeling artwork; its "rightness" is measured by internal
coherence and legibility, not by matching nature. The science below is used as
**orientation and inspiration**, in the same spirit as the references in the
[README](../README.md) — "orientation points, not endorsements or copied content."

---

## 1. Motivation

Two questions motivate this subsystem:

1. **Can Furkan Öztürk's homochirality research be an *input* to the simulation?**
   Öztürk's program shows how life's single-handedness (homochirality) can arise
   from a racemic (50/50) start through a *magnetically induced symmetry breaking*
   that then *self-amplifies and locks*. Crucially, his "central dogma of
   homochirality" treats chirality as **information** that propagates one-way
   through a network. That maps directly onto Evoverse's deterministic, event-
   sourced, trait-inheriting engine.

2. **"Is the brain producing thoughts the same as life producing lived
   experience?"** We answer this *structurally*, not metaphysically: Evoverse
   models both as the **same mechanism (symmetry breaking + one-way information
   propagation) applied at two different tiers**. Molecular homochirality turns
   *chemistry into life* (matter that carries heritable information → **lived
   experience**). A second, higher-order symmetry breaking — *cognitive
   homochirality* — turns *life into mind* (an internal model that commits to one
   coherent world-representation → **thought**).

This yields a single, testable-in-simulation thesis:

> **Homochirality is the symmetry breaking that lets information exist at all.
> Applied to molecules it produces life; applied to a lineage's internal model it
> produces thought. Same math, two tiers.**

---

## 2. Scientific lineage (references)

These are load-bearing for the *design intuition*, cited as orientation, not proof.

**Homochirality (Öztürk et al.)**

- S. F. Ozturk, Z. Liu, J. D. Sutherland, D. D. Sasselov, *Origin of biological
  homochirality by crystallization of an RNA precursor on a magnetic surface*,
  **Science Advances** 9 (2023). DOI
  [10.1126/sciadv.adg8274](https://www.science.org/doi/10.1126/sciadv.adg8274) ·
  open preprint [arXiv:2303.01394](https://arxiv.org/abs/2303.01394).
  *Racemic RAO (an RNA precursor) on magnetite → ~60% enantiomeric excess (ee),
  then 100% (homochiral) on a second crystallization. Two ingredients: (1) chiral
  symmetry breaking by the magnetic surface (CISS), (2) self-amplification by
  conglomerate crystallization.*
- S. F. Ozturk et al., *Chirality-Induced Avalanche Magnetization of Magnetite by
  an RNA Precursor*, **Nature Communications** (2023). Preprint
  [arXiv:2304.09095](https://arxiv.org/abs/2304.09095).
  *A feedback loop: enantiopure RAO magnetizes magnetite via CISS, and that
  magnetization spreads across the surface like an avalanche — a persistent,
  self-sustaining lock (~20 mT, exceeding the geomagnetic field).*
- S. F. Ozturk, D. D. Sasselov, J. D. Sutherland, *The central dogma of biological
  homochirality: How does chiral information propagate in a prebiotic network?*,
  **J. Chem. Phys.** (2023).
  [PMC7615580](https://pmc.ncbi.nlm.nih.gov/articles/PMC7615580/).
  *Chiral information flows one-way — RNA precursor → RNA → peptides → metabolites
  — analogous to Crick's central dogma.*
- S. F. Ozturk & D. D. Sasselov, *On the origins of life's homochirality: inducing
  enantiomeric excess with spin-polarized electrons*, **PNAS** (2022).
- *Life's homochirality: across a prebiotic network*, **PNAS** (2025), DOI
  [10.1073/pnas.2505126122](https://www.pnas.org/doi/10.1073/pnas.2505126122);
  and the 2026 feedback extension [arXiv:2605.19387](https://arxiv.org/pdf/2605.19387).

**Life–mind continuity**

- H. Maturana & F. Varela, *Autopoiesis and Cognition* (1980) — "living as a
  process is a process of cognition." The basis for treating thought as folded-over
  life rather than a separate module.

**Network view of brain and life (orientation, see §9 for how we cite it)**

- Prof. Dr. Türker Kılıç — network science / "connectivity" (bağlantısallık)
  framing: brain→mind and life→new information models may run on the *same
  mathematics*; information (not atoms) as the building block. Talk (question
  posed): *"Beynin düşünceler üretmesiyle yaşamın yaşantılar oluşturması aynı
  matematik sistem üzerinde yürüyor olabilir mi?"* —
  [YouTube](https://www.youtube.com/watch?v=_bL3qPHQheg).

---

## 3. Core concept: two nested symmetry breakings

| Tier | Symmetry breaking | Locks when | Produces |
|------|-------------------|-----------|----------|
| **T1 — Chemistry → Life** | *Molecular* homochirality: a region's `chirality_ee` leaves the racemic zone and locks to one hand | `|ee| ≥ ee_lock_threshold` | **Lived experience** — the universe carries states that are *about* survival; heritable information becomes possible |
| **T2 — Life → Mind** | *Cognitive* homochirality: a lineage's internal world-model collapses from "all possibilities weighted equally" (racemic mind) to one coherent commitment | `model_coherence ≥ mind_lock_threshold` | **Thought** — an internal representation that can predict and be *wrong* |

Both tiers share three moving parts, applied at different scales:

1. **Symmetry breaking** — a bifurcation out of an unstable balanced state.
2. **Avalanche lock** — a small bias amplifies and propagates to neighbours, then
   becomes irreversible.
3. **One-way information propagation** — the broken symmetry flows *downstream*
   only (region → species → offspring; environment → percept → model), never back.

---

## 4. Domain model additions

New fields on existing dataclasses in
[`backend/app/domain/models.py`](../backend/app/domain/models.py). `ee` = enantiomeric
excess ∈ `[-1, +1]`: `0` = racemic (no information), `+1`/`-1` = fully right/left-handed.

```python
@dataclass(slots=True)
class Universe:
    ...
    chirality_ee: float = 0.0          # global net handedness (mean of regions)
    homochirality_index: float = 0.0   # |mean ee| — GLOBAL single-handedness, 0..1
    local_order_index: float = 0.0     # mean |ee| — local order, blind to agreement
    domain_count: int = 0              # connected same-hand regions; 1 = one hand won
    chirality_locked: bool = False     # T1 gate latched (irreversible)

@dataclass(slots=True)
class Region:
    ...
    chirality_ee: float = 0.0          # local handedness; drifts, then avalanches
    chirality_locked: bool = False     # this region's T1 lock latched

@dataclass(slots=True)
class Species:
    ...
    chirality: int = 0                 # -1 / 0 / +1 handedness (0 until inherited)
    heterochiral_load: float = 0.0     # 0..1 mismatch burden ("scrambled" info)
    # --- T2 (only meaningful in the Intelligence Era) ---
    model_coherence: float = 0.0       # 0..1; racemic mind -> homochiral mind
    prediction_error: float = 0.0      # 0..1; |internal model - world|
    mind_locked: bool = False          # T2 gate latched for this lineage
```

`homochirality_index` is the **maturity metric** the rest of the product reads. It
is defined at three scopes:

- **Region:** `|region.chirality_ee|`.
- **Universe:** `|mean(region.chirality_ee)|` over non-collapsed regions.
- **Species:** `1 - heterochiral_load` (how cleanly the lineage carries one hand).

> **The universe scope is `|mean ee|`, not `mean |ee|` — and the difference is the
> whole subsystem.** `mean |ee|` measures *local* order: it reads `1.0` for a map
> split into equal and opposite domains, every region pure, none agreeing — a
> chiral glass, which is globally racemic. That is not a corner case; before the
> field term (§6.1) it was what actually happened on every seed measured. Life's
> homochirality is global — all of it runs on one hand — so the maturity metric
> and the Era gate must be global. `mean |ee|` is kept as `local_order_index`
> because the gap between the two *is* the domain problem, and `domain_count`
> names it directly.

---

## 5. `ChiralityRules` (hot-editable)

Add a frozen dataclass to
[`backend/app/simulation/rules.py`](../backend/app/simulation/rules.py) alongside the
existing rule groups, and register it so it flows through the `/admin/config`
draft → validate → apply → rollback path.

```python
@dataclass(frozen=True)
class ChiralityRules:
    # --- T1: molecular symmetry breaking (bifurcation) ---
    seed_bias_max: float = 0.02          # |initial ee| drawn from stable_rng(seed,"chirality")
    amplify_k: float = 0.06              # bifurcation gain; catalyst can raise this
    noise_scale: float = 0.03            # racemic-zone jitter, damped by |ee|
    field_strength: float = 0.005        # universe-wide field (the magnetized surface)
    ee_lock_threshold: float = 0.90      # |ee| at/above which the region latches
    # --- avalanche: locked region magnetizes neighbours (arXiv:2304.09095) ---
    avalanche_bleed: float = 0.05        # ee pushed to adjacent regions per tick
    avalanche_min_source: float = 0.75   # a region must be this homochiral to bleed
    # --- central dogma: one-way region -> species -> offspring ---
    inherit_flip_chance: float = 0.01    # rare, mostly-lethal chiral flip mutation
    heterochiral_growth_penalty: float = 0.35  # max growth loss for full mismatch
    heterochiral_lethal_load: float = 0.85     # load above which populations crash
    # --- T1 era gate ---
    life_gate_index: float = 0.80        # universe homochirality to leave Genesis/Expansion
    # --- T2: cognitive homochirality ---
    mind_gate_index: float = 0.92        # universe homochirality required before minds can form
    model_coherence_gain: float = 0.04   # per-tick pull toward a committed world-model
    mind_lock_threshold: float = 0.90    # model_coherence at/above which a lineage "thinks"
    prediction_decay: float = 0.15       # how fast prediction_error relaxes toward reality
```

Wire it into the registry in
[`backend/app/simulation/rule_config.py`](../backend/app/simulation/rule_config.py):

```python
SECTION_TYPES = {
    ...,
    "chirality": ChiralityRules,   # public key auto-becomes "chirality"
}
```

and add the field on `SimulationRules`. It then appears in the editable rules admin
([`docs/ADMIN_SIMULATION_CONTROLS.md`](ADMIN_SIMULATION_CONTROLS.md)) for free.

---

## 6. Tick rules (engine)

Added to the per-tick pass in
[`backend/app/simulation/engine.py`](../backend/app/simulation/engine.py). All
randomness goes through `stable_rng(seed, ...)` so the world stays deterministic and
replayable.

### 6.1 Molecular bifurcation + avalanche lock (T1)

The universe carries one **uniform field** — the direct analogue of Öztürk's
magnetized surface. Its sign is drawn once per seed and applies to every region:

```
B = +1 or -1, from stable_rng(seed, "chirality-field")   # contingent, but global
field = field_strength * B
```

For each **unlocked** region, per tick:

```
r   = stable_rng(seed, "chirality", region.id, tick)
noise = (r.random()*2 - 1) * noise_scale * (1 - |ee|)    # fades as the region commits
ee += amplify_k * ee * (1 - ee**2) + field + noise       # pitchfork, biased by the field
if |ee| >= ee_lock_threshold:
    region.chirality_ee   = sign(ee)                 # snap to full hand
    region.chirality_locked = True                   # irreversible latch
```

**Why the field is load-bearing, not decoration.** Öztürk's contribution is not
that symmetry breaks — Frank showed autocatalysis alone does that in 1953 — it is
that a *global field* breaks it the **same way everywhere**, which is why life is
L-handed across the whole planet rather than in patches. Without `field`, each
region amplifies whichever way its own local noise pushed, and the map freezes
into opposing domains: locked, locally pure, globally racemic. Measured over 10
seeds at 400 ticks: `field_strength = 0` gives **0/10** single-handed universes
(≈5 domains each); `0.002` gives 6/10; `0.005` gives **10/10**. Noise is damped by
`(1 - |ee|)` because it is a property of the region's own racemic jitter; the
field is not damped, because it is external and does not care how committed the
region already is.

The hand stays **contingent** — different seeds land on different hands — while
being **global**. That is the combination the mechanism exists to produce.

Then **avalanche**: every locked region with `|ee| >= avalanche_min_source` pushes
`avalanche_bleed * sign(ee)` into each adjacent region's `ee` (neighbours from the
hex layout, see [`frontend/lib/hexMap.ts`](../frontend/lib/hexMap.ts) / region x,y).
This reuses the existing "activity waves ripple to neighbours" intuition — a locked
hand spreads like magnetization across the map.

`Universe.chirality_ee` and `Universe.homochirality_index` are recomputed as the
region aggregates after this pass.

### 6.2 Chiral central dogma: one-way inheritance (T1 → biology)

At **speciation** (in the existing speciation rule):

```
child.chirality = parent.chirality
if stable_rng(seed,"chiralflip",child.id).random() < inherit_flip_chance:
    child.chirality *= -1                 # rare flip; see lethality below
```

A species with no hand yet (`chirality == 0`) adopts the **sign of its origin
region's locked ee** the first time that region locks. Information flows region →
species → offspring, never upstream.

### 6.3 Heterochiral selection pressure (T1 → populations)

In the population growth rule, add a chirality-match factor:

```
mismatch = 0 if region.chirality_ee == 0 else
           (species.chirality != sign(region.chirality_ee)) * |region.chirality_ee|
species.heterochiral_load = mismatch
habitat_score *= (1 - heterochiral_growth_penalty * mismatch)
if species.heterochiral_load >= heterochiral_lethal_load:
    apply a strong decline (models "scrambled" information — no viable storage)
```

Net effect: species are driven to migrate toward regions of their own hand, or die.
A flipped-hand mutant is almost always lethal — exactly Öztürk's point that mixed
chirality cannot store heritable information.

> **Measured: this rule is a transient, not a standing pressure.** On the base
> seed, mismatched populations exist only while regions are still locking — 17 at
> tick 60, 4 at tick 100, **0 from tick 140 onward, permanently**. Once every
> region has latched and every lineage has adopted a hand, the system is in an
> absorbing state: mismatch can no longer arise, because the mismatched
> populations are already dead and hands never change. In a 10,000-tick run,
> heterochiral selection does all of its work in the first ~80 ticks and is inert
> for the remaining ~9,900.
>
> That is the correct behaviour, not a bug — a symmetry break is a one-time event
> and this rule is what *enforces* it — but it means the subsystem must not be
> read as an ongoing ecological force. With the field on (§6.1) the only thing
> that can ever reawaken it is the `inherit_flip_chance` mutant, which now has no
> same-hand refuge anywhere on the map and dies wherever it appears. Before the
> field, a flipped mutant could migrate into an opposite-hand domain and survive —
> the domains were quietly making the flip mutation *survivable*, which is the
> opposite of the thesis this rule exists to express.

### 6.4 Two-tier Era gate — *implemented*

Previously `current_era` was set once to `Era.EXPANSION` in
[`seeder.py`](../backend/app/simulation/seeder.py) and never advanced. `_advance_era`
now runs each tick, driven by the maturity metric:

```
idx = universe.homochirality_index
if rank(era) < rank(STABILIZATION) and idx >= life_gate_index:
    era = STABILIZATION                    # T1 achieved: chemistry -> life
if rank(era) < rank(INTELLIGENCE) and idx >= mind_gate_index and any lineage mind_locked:
    era = INTELLIGENCE                      # T2 achieved: life -> mind
```

Progression is **monotonic** (an era is never lost) and each transition emits one
`ERA_ADVANCED` event. So **maturity is homochirality**, and the Intelligence Era is
*earned*, not seeded — it stays unreachable until the T2 tier (§6.5) sets
`Species.mind_locked`. On the base seed, Stabilization is earned around tick 44
(index ≥ `life_gate_index` = 0.80).

> **Monotonicity is enforced, not inherited.** This document used to say an era is
> never lost *because locked ee keeps the index from falling*. That was true only
> while the index was `mean |ee|`, which locking pins at 1 and which therefore
> could not fall. Global `|mean ee|` **can** fall: a region latching against the
> current majority drags it down. Eras survive that only because `_advance_era`
> compares `_ERA_RANK` and refuses to move backward — the guard is doing the work
> the metric used to do for free.
>
> The flip side is the point of the change: the gate can now be **failed**. With
> `field_strength = 0`, the base seed locks every region, reaches
> `local_order_index = 1.0`, and still never leaves Expansion, because its 108
> regions never agree on a hand. Under the old metric that same universe scored
> `1.0` and was handed the Stabilization Era at tick 68. A gate that always passes
> is not a gate; this one now discriminates.

### 6.5 Cognitive homochirality (T2)

Only runs once `universe.homochirality_index >= mind_gate_index`. For each
`stable`/`dominant` lineage:

```
model_coherence += model_coherence_gain * model_coherence * (1 - model_coherence)
                   + small stable_rng noise            # same bifurcation, higher tier
if model_coherence >= mind_lock_threshold:
    species.mind_locked = True                          # the lineage "thinks"
# a thinking lineage carries an internal world-model that can diverge from reality:
prediction_error += environment_change_this_tick
prediction_error -= prediction_decay * prediction_error # it corrects, imperfectly
```

`prediction_error > 0` is the signal that a *representation* exists that is distinct
from the world — the operational definition of a **thought** in Evoverse: a racemic
mind (all options equal) cannot act; a homochiral mind commits to one model and can
be wrong about the world. Same bifurcation as §6.1, one tier up.

---

## 7. Catalyst & events

- **New catalyst action `CHIRAL_PULSE`** (`CatalystActionType`): the observer's
  spin/magnetic bias — the direct analogue of Öztürk's magnetized surface. Pushes a
  region's `chirality_ee` toward a chosen hand (bounded, daily-limited, like the
  existing pulses). It is the *only* handle on symmetry breaking; observers nudge,
  the simulation decides. See [`docs/CATALYST_API.md`](CATALYST_API.md).
- **`SYMMETRY_BREAK` event** (`EventType`) — *implemented (T1)*. Fires on three
  scoped transitions, carried in `payload.scope`: `"region"` (severity 4) for the
  universe's **first** molecular break (not every region — that would flood the
  chronicle); `"lineage"` (severity 3) each time a species commits a hand; and
  `"universe"` (severity 5, once) when every viable region has latched. Payload also
  carries `hand`/`hand_sign` (and `homochirality_index` for the universe scope). A
  rare lethal `chiral flip` rides the existing `MUTATION_DETECTED` event with a
  `chiral_flip: true` payload flag (selection culls it — no separate event needed).
  Contracts live in `event_payloads.py`; see also
  [`docs/EVENT_PAYLOAD_SCHEMAS.md`](EVENT_PAYLOAD_SCHEMAS.md).

---

## 8. Visualization hooks (see companion three.js "Organism Lens")

The maturity metric gates the close-up inspector:

- **Below `life_gate_index`:** a lineage renders only as a 2D point/sprite in the
  Micro Life Field; the "Inspect" affordance is **locked** (racemic = no stable
  form).
- **Region locked + species `stable`/`dominant`:** a 3D **Organism Lens** unlocks
  (lazy `next/dynamic`, `ssr:false`). The body is generated *deterministically* from
  the species state (`stable_rng` mirror of the backend), so the form is a readout
  of the model, not arbitrary art. `species.chirality` sets the **coil direction**
  of the organism's helices/shell — you can literally *see* the hand; high
  `heterochiral_load` makes the form visibly conflicted.
- **`mind_locked` lineage:** the Lens gains a second mode showing the lineage's
  **internal world-model** as a small 3D representation that can diverge from the
  real universe — thought made inspectable, side by side with reality.

---

## 9. On citing Prof. Dr. Türker Kılıç (and using convergence honestly)

Kılıç's network-science thesis — that brain→mind and life→new-information-models may
run on the *same mathematics*, with information as the building block — is
**genuinely convergent** with this design's two-tier "same math, two tiers" framing.
Citing him is appropriate **as intellectual orientation and motivation**, exactly
how the README frames all references.

It is **not** appropriate to present the convergence as *validation* that Evoverse
is scientifically correct. That would be two fallacies at once: appeal to authority,
and confirmation bias (a design built to embody an idea "agreeing with" that idea
proves nothing). Kılıç's "same mathematics" is itself a vision/hypothesis, not a
proven theorem; citing a vision to validate a model that shares it is circular.

The honest and defensible claim is:

> Evoverse independently arrives at a two-tier symmetry-breaking model of
> life-and-mind that *resonates* with Öztürk's homochirality-as-information program,
> Maturana–Varela's life–mind continuity, and Kılıç's network-mathematics framing.
> We treat this convergence as evidence of **design coherence and a well-chosen
> direction — not as empirical proof about biology.**

Cite Kılıç under "orientation points," attribute the exact question to the talk, and
keep the "it validates us" language out. Convergence is a compass, not a certificate.

---

## 10. Non-goals & open questions

- **Non-goal:** claiming Evoverse simulates real prebiotic chemistry or real
  cognition. These are legible *analogues*, tuned for observability.
- **Open:** whether T2 should be per-lineage or per-region; how prediction_error
  should feed back into behaviour (does a wrong model change migration?); whether
  `CHIRAL_PULSE` should be observer-only or also an emergent regional event.
- **Open:** exact thresholds in §5 are first guesses; they belong in the hot-
  editable rules so they can be tuned against 10k-tick benchmarks
  ([`backend/app/simulation/benchmark.py`](../backend/app/simulation/benchmark.py)).

---

## 11. Suggested build order

1. **T1 backend slice — DONE:** `chirality_ee` + bifurcation/avalanche (§6.1) +
   `ChiralityRules` + `homochirality_index` on the API and in persistence
   (migration `008_chirality_field.sql`). Determinism covered in
   `backend/tests/test_chirality.py` and the benchmark signature.
2. **Inheritance + selection (§6.2–6.3) + `SYMMETRY_BREAK` event — DONE:** one-way
   `Species.chirality` adoption/inheritance with a lethal chiral-flip mutation,
   heterochiral growth/lethal selection, and scoped symmetry-break events. On the API
   (`chirality`, `heterochiralLoad`) and persisted (migration
   `010_species_chirality.sql`). Covered in `backend/tests/test_chirality.py`.
3. **Era gate (§6.4) — DONE:** `_advance_era` promotes Expansion → Stabilization
   (homochirality) and Stabilization → Intelligence (homochirality + a mind-locked
   lineage, so unreachable until T2), monotonically, with an `ERA_ADVANCED` event.
   `current_era` was already persisted. Covered in `backend/tests/test_chirality.py`.
3b. **Global field + global metric — DONE:** `field_strength` (§6.1) makes the
   break homochiral rather than merely locked (0/10 → 10/10 single-handed universes
   across seeds), and `homochirality_index` became `|mean ee|` with
   `local_order_index` / `domain_count` alongside it (§4, §6.4). Together these fix
   a gate that previously handed the Stabilization Era to globally racemic
   universes. Covered in `backend/tests/test_chirality.py`.
4. **Organism Lens** (three.js) reading the maturity metric (§8).
5. **T2 cognitive tier (§6.5)** + the Lens's world-model mode.
