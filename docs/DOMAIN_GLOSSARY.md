# Evoverse Domain Glossary

## Universe

The top-level simulation space. Phase-1 runs only Alpha, but the code keeps the boundary open for Beta and Gamma.

## Region

A grid cell inside a universe. Regions own biome, energy, resource density, stability, and dominant species state.

## Species

A species-level life form. Phase-1 does not simulate individual organisms; species are tracked through aggregate populations per region.

## Population

The aggregate count of a species inside a region. Population growth, decline, migration pressure, mutation chances, and event generation operate from this layer.

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

The universe's **maturity metric**: the mean `|ee|` over non-collapsed regions, in `[0, 1]`. `0` = racemic chemistry, `1` = every viable region is fully single-handed. It gates the Era progression.

## Lineage chirality & heterochiral load

A species' committed handedness (`chirality`, `-1/0/+1`) is adopted one-way from its origin region's locked hand and inherited at speciation (the "chiral central dogma"), with a rare, usually lethal flip mutation. `heterochiral_load` (`0..1`) is the mismatch burden of a committed lineage sitting in an opposite-hand region — it taxes growth and is lethal past a threshold.

## Era

An earned stage of maturity: `Genesis → Expansion → Stabilization → Intelligence`. Progression is monotonic and gated by the homochirality index — **Stabilization** is earned when it crosses `life_gate_index` (chemistry → life), **Intelligence** when it crosses `mind_gate_index` *and* a lineage's mind has latched (life → mind; the cognitive tier is not yet driven). Each transition emits an `ERA_ADVANCED` event.

## Symmetry break

The moment chiral symmetry breaks irreversibly. Emitted as a `SYMMETRY_BREAK` event at three scopes: the universe's first `region` break, each `lineage` committing a hand, and the whole `universe` reaching full homochirality.
