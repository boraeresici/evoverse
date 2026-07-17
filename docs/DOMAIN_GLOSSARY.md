# Evoverse Domain Glossary

## Universe

The top-level simulation space. Phase-1 runs only Alpha, but the code keeps the boundary open for Beta and Gamma.

## Region

A grid cell inside a universe. Regions own biome, energy, resource density, stability, and dominant species state.

`resource_density` is the one region field **life feeds back into**: each tick a region loses `sum(population × energy_consumption) / consumption_pressure_scale` to whatever lives on it (see *Consumer–resource draw*). Energy and stability drift on their own noise regardless of what the region carries.

`last_reported_resource_density` is bookkeeping, not state anyone should read as a fact about the world: it is the level the chronicle last reported, and a resource-shift event is a move away from *it* rather than from last tick.

## Species

A species-level life form. Phase-1 does not simulate individual organisms; species are tracked through aggregate populations per region.

## Population

The aggregate count of a species inside a region. Population growth, decline, migration pressure, mutation chances, and event generation operate from this layer.

`decline_reference_population` is the high-water mark a decline is measured down from — it rises with the population and resets whenever a decline is reported. Growth here is ~+0.6%/tick and the worst single tick loses ~11%, so "lost a fifth since last tick" describes nothing this world can do; "lost a fifth since its peak" is a story it tells constantly.

## Consumer–resource draw

What a region's populations take out of it each tick: `sum(population × energy_consumption) / consumption_pressure_scale`, read from the counts the previous tick left. It is the model's only closed ecological loop, and three things fall out of the one term:

- **A carrying capacity.** Density pressure throttles a population by its *own* size; nothing tied the ceiling to the world, so growth simply kept climbing. With the draw it is bounded.
- **Interspecific competition, for free.** Two species in one region drink from the same well: a neighbour's headcount arrives as a lower `resource_density` in your habitat fit. No competition rule is written — it is the resource.
- **Overgrazing.** A region can be drawn under its equilibrium by what lives on it.

## Traits

Numerical properties that influence species behavior:

- efficiency
- adaptation
- cooperation
- mobility
- resilience

## Event

A durable simulation fact used by Chronicle, Region/Species timelines, Replay Lite, Forecast Lite, and future Time Zoom.

## Catalyst Action

A limited, regional user influence. It never creates species directly and never applies globally.

## Chirality (enantiomeric excess, `ee`)

A region's net molecular handedness, in `[-1, +1]`: `0` is racemic (no committed hand), `±1` is fully right/left-handed. It drifts through a bifurcation, latches irreversibly once it crosses the lock threshold, and spreads its hand to neighbours (avalanche). Inspired by S. Furkan Ozturk & Dimitar Sasselov's homochirality research; see [`CHIRALITY_AND_MIND.md`](CHIRALITY_AND_MIND.md).

## Homochirality index

The universe's **maturity metric**: `|mean ee|` over non-collapsed regions, in `[0, 1]` — the *global* single-handedness. `0` = the map has no net hand, `1` = every viable region agrees on one. It gates the Era progression.

It is deliberately **not** `mean |ee|`. That measures local commitment and reads `1.0` for a map split into equal and opposite domains — every region pure, none agreeing, and globally racemic. Life's homochirality is global (all of it runs on one hand), so the gate must be global. `mean |ee|` is kept as **`local_order_index`**, because the gap between the two *is* the domain problem.

## Local order index & domain count

`local_order_index` is `mean |ee|`: how far regions are from racemic *locally*, blind to whether they agree. `domain_count` is the number of connected same-hand regions (von Neumann adjacency; collapsed regions are holes). `domain_count == 1` is the real signature of homochirality — one hand won the whole map. A universe with `local_order_index = 1.0` and `domain_count = 5` is a **chiral glass**: fully latched, fully committed, and globally racemic.

## Symmetry-breaking field & racemization

`field_strength` (β) is the universe-wide field — the analogue of Ozturk & Sasselov's magnetized surface. Its sign is drawn once per seed, so *which* hand a universe gets is contingent while being **global**. Without it, each region amplifies whatever its own noise chose and the map freezes into domains.

`racemization_rate` (λ) is the thermal back-reaction pulling any excess toward 50/50. Amplification must beat it: the pitchfork's control parameter is `μ = amplify_k − racemization_rate`, and at `μ ≤ 0` racemic is stable and no hand ever forms. Together the two lay out a plane with four phases — see [`CHIRALITY_AND_MIND.md` §6.6](CHIRALITY_AND_MIND.md) or run `make phase`.

## Lineage chirality & heterochiral load

A species' committed handedness (`chirality`, `-1/0/+1`) is adopted one-way from its origin region's locked hand and inherited at speciation (the "chiral central dogma"), with a rare, usually lethal flip mutation. `heterochiral_load` (`0..1`) is the mismatch burden of a committed lineage sitting in an opposite-hand region — it taxes growth and is lethal past a threshold.

**It is a transient, not a standing pressure.** Measured on the base seed, mismatched populations run 17 at tick 60, 4 at tick 100, and **0 from tick 140 onward, permanently**: once every region has latched and every lineage has adopted, mismatch can no longer arise. In a 10,000-tick run the rule does all its work in the first ~80 ticks. That is correct — a symmetry break is a one-time event and this rule is what enforces it — but it must not be read as an ongoing ecological force.

## Era

An earned stage of maturity: `Genesis → Expansion → Stabilization → Intelligence`. Progression is monotonic and gated by the homochirality index — **Stabilization** is earned when it crosses `life_gate_index` (chemistry → life), **Intelligence** when it crosses `mind_gate_index` *and* a lineage's mind has latched (life → mind; the cognitive tier is not yet driven). Each transition emits an `ERA_ADVANCED` event.

## Symmetry break

The moment chiral symmetry breaks irreversibly. Emitted as a `SYMMETRY_BREAK` event at three scopes: the universe's first `region` break, each `lineage` committing a hand, and the whole `universe` reaching full homochirality.
