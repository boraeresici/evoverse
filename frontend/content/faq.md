# Science & model

## Will the map cells ever merge as life expands?

No. The map is a fixed spatial substrate — 108 regions on a 12x9 grid, placed by real coordinates. Think of a region as permanent geography (a biome), not as an organism. Regions never merge or split.

Expansion happens on two axes without changing the grid:

- Spatial: a species grows inside a region up to a density-pressure cap, then migrates to neighbouring regions. "Spreading" is migration across the fixed grid.
- Lineage: growth from a single ancestor happens through speciation — new species branch off by mutation. This is what the phylogenetic tree shows as radiation.

## What keeps the universe from exploding or dying out?

A balancing loop, tuned against a 10,000-tick benchmark to stay viable:

- Growth is bounded per region by a density-pressure cap.
- Overloaded regions shed population through migration to neighbours.
- Diversity branches through speciation instead of unbounded single-species growth.
- Regions that overshoot or deplete resources collapse, then recover; region drift reverts toward equilibrium.

Capacity is managed by per-region caps plus collapse/recovery and equilibrium reversion — not by changing the grid topology. That is why cell merging is unnecessary.

## Is this Conway's Game of Life?

It shares the spirit — a seeded grid, discrete ticks, local rules, and emergence read over time — but it is not a binary B3/S23 clone. Each cell is raised into a region aggregate (energy, resources, stability, collapse state, dominant species, population) so the product can explain ecology, history, and intervention, not only cell survival. See [Purpose](/purpose) and [Resources](/resources).

## Are the little organisms in the Micro Life View real individuals?

No. The Micro Life View is a deterministic, sampled visualization of a region's aggregate signals (population, energy, species share, events). It is a legible representation, not a per-individual simulation, so there is no individual accounting that would require merging or splitting.

## Why is the number of hexagons fixed if life keeps expanding?

Because hexagons are the world, not the life in it. The 108 regions are fixed geography — like continents. Life expands *across* and *within* that fixed geography: population grows inside regions (up to a cap), migrates to neighbours, and diversifies through speciation. Earth's continents did not multiply as life radiated; the world stayed fixed while life filled it.

A fixed grid is also a deliberate product choice: it keeps the map learnable (you can track *where* over time), keeps computation and reports legible, and lets the balancing loop manage capacity per region instead of growing the map. Growing the grid is possible later, but only as an explicit design decision (see the previous question).

## Could unbounded expansion be modelled later?

Yes, as a future product decision — for example region subdivision (a region splits into sub-cells), carrying-capacity scaling with traits, or additional seeded universes. The current model is intentionally a fixed-grid ecology rather than a 4X-style expansion game.

## What do "flocking", "reach" and "patches" mean on the Science page?

They are our words, not the field's. The Science page asks a question borrowed from statistical physics, and physics has its own names for every part of it. We use plain ones so the page can be read without a background in the subject — but if you go looking for the literature, our words will not find it. Here is the mapping, so you can.

- "Does Alpha flock?" is, in the literature, "is the system critical?" or "does it show scale-free correlations?". Nothing in physics is called flocking — the flock is simply where the phenomenon was famously measured, in [Cavagna et al., "Scale-free correlations in starling flocks", PNAS 107(26), 2010](https://www.pnas.org/doi/10.1073/pnas.1005766107).
- The "reach curve" is the correlation function, written C(r). It measures how strongly two points agree, as a function of how far apart they are.
- "Reach" as a single number is the correlation length, written ξ (xi). It is where C(r) first crosses zero: the distance past which agreement stops meaning anything.
- "Patches" are domains, or clusters — neighbouring regions ruled by the same species. Physics asks whether their sizes follow a power law, P(s) ∝ s^−τ.
- "At floor" is not a term at all, ours entirely. It means ξ landed at the smallest distance the grid can express, one region across, so the true value sits somewhere below that and only an upper bound can be reported. Distances on a fixed grid are whole numbers; there is nothing between neighbours.

The measurement itself is not simplified anywhere. The page checks its own arithmetic against the constraint the starling paper proves, and leaves a number out when the evidence cannot carry it rather than rounding it into confidence. Only the vocabulary is ours.

## Why does the Science page leave some numbers blank?

Because it can compute them and they would not mean anything, and a printed number gets believed and quoted.

Two examples. Alpha currently has eleven patches across three distinct sizes; the code can fit a power law to that and reports a 99.9% fit, but a line through three points is a fact about three points, not about Alpha. And the pattern-trigger tables score how much likelier a pattern is under given conditions — when a pattern appears exactly once, under conditions that also appear exactly once, the arithmetic can only return the total number of observations, so a "score of 30" out of 30 observations is the sample size, not a finding.

So those slots stay visibly empty with the requirement written in, rather than greyed out. A faded number is still read.

# Simulation mechanics

## Is the simulation deterministic and reproducible?

Yes. The engine advances in discrete ticks from a fixed seed, and randomness is drawn from seeded, context-keyed streams rather than wall-clock entropy. The same seed and rules reproduce the same universe, which is what makes benchmarks, snapshots, and replay trustworthy.

## Why model aggregate populations instead of individual organisms?

Because the product needs explainable ecology, not maximal micro-realism. Each region tracks per-species population, growth, and migration pressure as aggregates, so the system can answer "what changed, where, and why" and keep long runs computationally bounded. The Micro Life View then samples those aggregates into a visible field — legibility over literal individuals.

## How do new species form?

Through speciation: when a population crosses mutation and size thresholds, a child species branches off a parent with shifted traits. This is the radiation you see in the phylogenetic tree — a lineage diversifying over world age rather than a single population growing without end.

## Is there natural selection or fitness?

Indirectly. Species carry traits (efficiency, adaptation, cooperation, mobility, resilience) that feed growth, migration, and resilience against decline and collapse. Better-suited lineages persist and radiate; poorly-suited ones decline toward extinction. It is a pressure model, not a per-individual genetic algorithm.

## What makes a region collapse — and recover?

A region collapses when its stability and resources fall below viability thresholds; it recovers when they climb back above recovery thresholds. Region drift also reverts toward an equilibrium, so long runs stay viable instead of every region collapsing. Collapse and recovery are the ecology's pressure valve.

## How does population spread between regions?

Migration. When a region's population and migration pressure are high enough, some of it moves to neighbouring regions on the hex grid. Because regions are placed by real coordinates, spread reads spatially — a wave moving across neighbours rather than teleporting.

## How is the catalyst different from playing god / direct control?

The catalyst applies bounded influence (energy pulse, mutation pulse, resource burst) to a region, subject to quota and cooldown, and then the simulation decides the downstream effect. You nudge conditions; you do not script outcomes. Observation with limited intervention is a deliberate design stance.

# Using Alpha

## How do I read the universe map?

Each hexagon is a region coloured by the selected mode (Life, Energy, Mutation, Stability). Hover for its dominant species and population; click to open the region. Recent events ripple outward to neighbouring regions, and the whole field breathes with global stability.

## How does time travel work?

On the universe map, drag the time scrubber or press Play to redraw the map from historical snapshots. Era bands and Time Zoom frame the Alpha Age; press Live to return to the present.

## Does the chronicle ("What Alpha Recorded") grow endlessly?

The underlying event log is append-only and permanent, but the chronicle page never renders all of it at once. It shows a bounded page (up to ~50, capped at 100 in live mode) filtered by the time window you pick — Now, Last 24h, Last 7d, or All History. So the page has a fixed maximum length; older events stay in history and are reached by narrowing the filter rather than by an ever-growing list.

## What is "Alpha Age"?

Alpha Age is the world age of the simulation — an in-world time counter, not a wall-clock date. The literal mapping of ticks to calendar time is an open product decision, so cadence labels (daily/weekly digests, era bands) currently use tunable placeholders.

# Roles & interaction

## What can an Observer do?

Follow regions and species, receive in-app notifications, and read a personal Following Digest. Observer actions are identity-scoped and never expose raw simulation internals.

## What is a Catalyst?

A Catalyst can apply bounded influence to a region (energy pulse, mutation pulse, resource burst) subject to role, quota, and cooldown. Catalyst access is invite/role gated; Alpha decides the downstream effect.

## Who can change simulation rules?

Only admin accounts. The editable rules screen at `/admin/config` is gated: non-admin identities cannot open the editor, and the backend rejects rule writes and destructive resets without an active admin role.

# Data & history

## Is Alpha persistent?

Yes. State lives in PostgreSQL and is shared by the API and the background worker. The event log is append-only, and tick-level plus entity-level snapshots power reports, replay, and time navigation.

## Can I export what I see?

Species detail offers a shareable PNG species card and a JSON export. Reports and comparisons are chart-ready, and the chronicle streams live events.
