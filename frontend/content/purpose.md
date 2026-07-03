# Make artificial life observable, explainable, and product-ready.

Evoverse is being built as a persistent artificial life observatory: a living product surface where simulation state, evolution, intervention, and historical comparison are understandable without reading backend internals.

## Conway lineage

Evoverse starts from the spirit of Conway's Game of Life: a seeded grid, discrete ticks, local rules, and emergent behaviour that becomes meaningful only when observed over time.

It is not a direct B3/S23 clone. Classic Game of Life uses binary cells, where each square is alive or dead and the next generation is decided by neighboring live-cell counts. Evoverse uses an aggregate region/population/species model because the product needs explainable ecology, historical reports, intervention traces, and species-level continuity rather than only cell survival.

The current relationship is best read in three layers:

- Direct algorithmic link, 32/100: Evoverse does not apply binary cell state, Moore-neighborhood survival, or exact B3/S23 update rules.
- Simulation approach link, 72/100: both systems share grid state, seeded initialization, discrete ticks, emergence, pattern reading, and simple rules producing macro behaviour.
- Product lineage, 56/100: Evoverse expands the Game of Life idea into a persistent artificial-life observatory with regions, species, resources, interventions, events, and reports.

## Why aggregate regions instead of binary cells

Binary cells are excellent for pure emergence, but they hide product-level meaning. Evoverse keeps each map cell as a region with energy, resources, stability, collapse state, dominant species, and population composition so the user can ask richer questions: what changed, where did a species move, why did a region collapse, and whether the universe is becoming more stable.

This model combines several approaches:

- Cellular automata inspiration for grid, seed, ticks, and emergent observation.
- Agent/ecology simulation for species traits, population growth, decline, migration, and speciation.
- Resource-and-stability dynamics for regional pressure, collapse, and recovery.
- Event sourcing and snapshots for chronicle, replay, comparison, and dynamic reporting.
- Human-in-the-loop catalyst actions for controlled intervention without losing simulation continuity.

## Persistent world state

Alpha keeps running across ticks, snapshots, events, and region/species histories.

## Genesis

Genesis explains how Alpha moves from a deterministic seed into a living observatory. It is the bridge between Conway's initial-pattern idea and Evoverse's aggregate region/species ecology.

[Genesis Notes](/genesis)

## Legible emergence

The product turns simulation events into readable signals instead of hiding them in logs.

## Evolutionary pressure

Species react to resources, stability, mutation, migration, collapse, and catalyst actions.

## Measurable progress

Reports and observability show whether the universe becomes richer, quieter, or unstable.

## Product direction

The current foundation prioritizes persistence, worker/API separation readiness, governance, notifications, analytics, and dynamic reporting. The next product layer turns this into investigation tools: map modes, comparison charts, replay, and deeper species genealogy.

[Reference Shelf](/resources)
