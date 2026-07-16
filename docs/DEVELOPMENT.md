# Evoverse — Development & Approach

Evoverse is a persistent artificial-life observatory. Its first universe, **Alpha**,
is a seeded world in which regions, species, populations, and chronicle events
evolve through a deterministic tick engine. This document is the narrative of *how*
and *why* Evoverse was built the way it is. It is not an API reference — those live
alongside it in `docs/` — and it is not a sprint log. It is a design essay about the
modeling choices, the scientific lineage, and the engineering boundaries that give
the project its shape.

The guiding intuition is simple to state and consequential to honor: a user should
open Alpha and, within a few seconds, feel that it is *alive* and has a *history*.
Everything below serves that intuition — the aggregate ecology, the event-sourced
data spine, the macro/micro split, and above all the ability to travel not only
through space but through time.

---

## 1. Overview & Vision

Evoverse is deliberately *not* a game, a sandbox, or a Conway clone. It is a
continuously running digital world where artificial life forms emerge, speciate,
migrate, form habitats, decline, and occasionally collapse. Users **observe** this
process and may nudge it through bounded catalyst effects, but they cannot control
it directly. The simulation always retains authority over outcomes.

Three roles frame the experience:

- **Guest** — anonymous. Watches the universe, inspects species, reads history.
- **Observer** — a registered user who follows species, favorites regions, and
  receives notifications, building a personal reason to return.
- **Catalyst** — a registered user with a small daily budget of *regional*
  interventions (energy, mutation, and resource pulses). A Catalyst cannot create
  life, invent species, or reset the world; they can only start an influence and
  let the simulation decide what happens.

The architecture anticipates multiple universes (Alpha, Beta, Gamma) so that future
worlds can run under different regimes — high mutation, low energy, aggressive
evolution — and be compared. For now only Alpha runs, but the domain model treats it
as one instance of many rather than the singular world.

The largest product risk was never technical. It was **interest**: why would anyone
come back tomorrow? The answer designed into the product from the first day is a
living record — a Chronicle of what happened in Alpha, plus the ability to follow a
species or region and be told when its story advances. The long-term differentiator
is that Evoverse offers not just *space navigation* but *time navigation*.

---

## 2. Scientific Lineage: From Conway to Aggregate Ecology

Evoverse begins from the spirit of Conway's Game of Life and then deliberately
diverges. That divergence is the central modeling decision of the project, so it is
worth being precise about what is shared and what is not.

### What Life gives us

Conway's Game of Life is a two-state cellular automaton on a two-dimensional grid.
Each cell is alive or dead and is updated simultaneously each generation according to
its eight neighbours under the B3/S23 rule. Its enduring lesson is that very simple
*local* rules can produce unexpected *global* behaviour — still lifes, oscillators,
gliders, guns, long-lived chaos, and even Turing completeness. The shared inheritance
Evoverse claims from this tradition is real and specific:

- a **seeded grid** as the spatial substrate,
- **discrete ticks** as the unit of time,
- **local rules** that produce emergent macro behaviour,
- and the practice of **reading pattern and history over time** rather than
  scripting outcomes.

### Why Evoverse is not a binary automaton

Evoverse does **not** implement B3/S23, binary cell state, or a simultaneous Moore
neighborhood update. A binary automaton is superb at *demonstrating* emergence but,
at the product level, it cannot answer the questions Evoverse exists to answer:
*what* changed, *where* it changed, *which* species were affected, and whether the
world is trending toward stability or collapse. A dead-or-alive cell has no room for
that context.

So each grid cell is raised from a bit into a **region aggregate**. A region is not
alive or dead; it carries `energy_level`, `resource_density`, `stability`, a
`collapsed` flag, a `biomeType`, a `lifeIndex`, a dominant species, and a
composition of populations. Life itself is modeled not as individual cells but as
**species and population records** layered over the regions.

An internal alignment study framed the relationship honestly rather than
marketing it: the *direct algorithmic* tie to Life is modest, the *simulation-approach*
tie (grid, seed, tick, emergence, observation) is strong, and the *product-lineage*
tie is the honest middle — Evoverse is born from Life's structural and philosophical
idea, then extended into a higher-level ecology with species, resources, catalysts,
and observability. The positioning that came out of that study:

> Evoverse starts from the spirit of Conway's Game of Life, then expands it into a
> persistent artificial-life observatory with species, regions, resources,
> interventions, and historical reports.

The lineage is deliberate, not accidental — and it is lineage, not replication.

### A second scientific input: homochirality as a maturity mechanic

Beyond the cellular-automata lineage, a planned subsystem takes an input from
origin-of-life chemistry: S. Furkan Ozturk & Dimitar Sasselov's work on **biological
homochirality** — how life's single-handedness arises from a racemic start through a
magnetically induced symmetry break that self-amplifies and *locks*, and how that
handedness then propagates as one-way *information* (their "central dogma of
homochirality"). Evoverse models this as a **chirality field**: a per-region
enantiomeric excess that drifts through a bifurcation, latches irreversibly, and
avalanches to neighbours, with the universe-level *homochirality index* serving as a
single **maturity** metric. The same mechanism, applied a tier up to a lineage's
internal world-model, frames the "life → mind" question. The full design — fields,
`ChiralityRules`, the two-tier Era gate, and the references — lives in
[`CHIRALITY_AND_MIND.md`](CHIRALITY_AND_MIND.md); the T1 slice (field + bifurcation +
homochirality index) is implemented and covered by determinism tests.

---

## 3. Simulation Model & Determinism

### A bounded ecology, not a growing colony

Alpha is a **finite** world: a fixed `12 × 9` region grid — 108 regions — that never
grows. This is a deliberate departure from Life, where the population of live cells
expands and contracts across an unbounded plane. The region grid is a **fixed spatial
substrate**, a stable map on which ecological state changes, rather than a set of
cells that are born and die as geography. Keeping the substrate fixed is what makes
the map legible, comparable across time, and cheap to snapshot; the *dynamics* live in
the region metrics and the populations, not in the shape of the world.

Each tick advances Alpha through a small, ordered set of rules:

- **Region drift** — energy, resources, and stability move, but pulled back toward an
  equilibrium rather than wandering freely.
- **Population growth and decline** — computed from habitat fit and density pressure,
  on the aggregate population of a species within a region.
- **Migration** — populations spill toward *orthogonally adjacent* regions. Neighbour
  relationships are used here only; there is no Moore eight-neighbourhood rule.
- **Speciation** — trait mutation and a speciation interval split off child
  populations, establishing parent-child lineage.
- **Status update and universe stability** — regions may collapse or recover, and a
  global stability index is recomputed.

### The bounded-ecology loop

The reason Alpha stays *interesting* over long runs is a set of counter-pressures
that keep it away from both extinction and runaway growth:

- **Density caps and pressure** keep any single population from exploding without
  bound within a region.
- **Migration** relieves local pressure and spreads life across the map.
- **Speciation** introduces novelty; **decline and extinction** remove it.
- **Collapse and recovery** let a region fail and later heal. **Equilibrium
  reversion** drifts region metrics back toward viability so that a long run does not
  simply flatline into universal collapse.

These were not free parameters left to chance. They were **tuned against a default
10,000-tick benchmark**: without equilibrium reversion and collapse recovery, long
runs tended to collapse every region; without calming speciation and growth rates,
species generation ran away after recovery. A representative benchmark run settles
around 2 of 108 regions collapsed, roughly 73 species, and on the order of 73,000
total population — a world that is neither dead nor exploding, which is exactly the
regime a persistent observatory needs.

That population figure used to read 162,000, and the difference is the point: it
was never a ceiling, only where the run happened to be when the benchmark stopped.
Nothing tied a population to the world it lived in — `energy_consumption` was
computed and stored and read by nothing — so growth had no upper bound and simply
kept going: 92k at 2,000 ticks, 162k at 10,000, 255k at 15,000. Regions now pay for
the life they carry, and the number is bounded instead of merely young. See
[`SIMULATION_FLOW_AND_FORMULAS.md` §3](SIMULATION_FLOW_AND_FORMULAS.md).

### Determinism and reproducibility

Determinism is a first-class requirement, not an afterthought. A **seeded random
utility** produces a reproducible initial distribution of regions, species, and
populations, and the tick rules are deterministic given that seed. The consequences
compound throughout the product:

- The same seed replays the same history, which is what makes Replay and time travel
  trustworthy rather than decorative.
- The benchmark emits a **determinism signature** so that a change in engine behaviour
  is visible as a change in that signature, and a **determinism smoke test** guards
  against accidental non-reproducibility.
- Simulation thresholds — mutation and speciation rates, collapse and recovery
  thresholds, Catalyst limits — are **centralized in a single rules module** rather
  than scattered through the code, so the world's behaviour is described in one
  place and can be governed as configuration.

Time is measured in ticks internally, but users never see ticks. They see **Alpha
Age** and **Era**. Raw tick ids, cycle numbers, RNG seeds, internal thresholds, and
worker status are kept out of user-facing language on principle; they surface only in
admin and debug tooling.

---

## 4. Data Architecture: Event Store, Snapshots, Reports

Evoverse's data spine is built to serve two very different reads: "what is Alpha like
right now" and "what was Alpha like *then*". It resolves this with a clean separation
between an append-only event log and a family of snapshots.

### Append-only event store

Every meaningful occurrence — speciation, decline, mutation, resource shift, collapse,
recovery, and Catalyst action — is written to an **append-only event store**. Current-state
saves never delete Chronicle history; the log is the durable record. Event payloads
carry a **versioned v1 envelope** (`schemaVersion`, `schema`, `eventType`), and legacy
persisted payloads are normalized on load, so the contract can evolve without
rewriting history. Each event carries a severity, a title, and a summary generated
from templates, which is what lets the Chronicle read as prose rather than as rows.

### Snapshots, separate from events

Alongside the event log, Alpha's entities are persisted as **current-state snapshots**
(universe, region, and species tables), and tick-level **summary snapshots** are stored
separately in a dedicated `universe_snapshots` table. Entity-level detail —
`region_snapshots`, `species_snapshots`, and `population_snapshots` — provides the
coverage needed for Time Zoom, Replay, and reporting to reconstruct a past moment.
The distinction between *event* (something happened) and *snapshot* (this is the state
at a tick) is kept sharp; conflating them would make history ambiguous.

### Dynamic Report

On top of snapshots sits a **Dynamic Report** surface that returns chart-ready series
plus baseline/current values and deltas across universe, region, species, and
population scopes. This is the comparison layer — the thing that answers "is this
region better or worse than it was" — and it feeds the report, comparison, and
micro-life surfaces without asking the frontend to compute anything itself.

### Realtime delivery

The Chronicle is delivered live over **server-sent events**, with `Last-Event-ID` /
`lastEventId` cursor support and a polling fallback, so a browser can watch events
arrive as the worker produces them without holding a fragile long connection.

A standing discipline runs through all of this: the frontend performs no critical
calculation of its own. State, deltas, and forecasts are produced server-side and
consumed by the client; the client's job is to render and to navigate.

---

## 5. Experience & Visualization Approach

The experience layer is where the "living history" thesis becomes visible. Several
decisions here are load-bearing.

### Macro map vs. micro life field

A design tension surfaced early: the region grid reads Alpha's macro state
efficiently, but a value like *5,098 population* is an aggregate — it does **not**
mean 5,098 sub-cells or individuals drawn inside a region. Evoverse Phase-1 does not
simulate individuals. Showing an aggregate metric alone weakened the felt sense of
life, even though the number was correct.

The resolution was a two-layer view, settled in a dedicated decision record:

- **Macro view** — the universe map stays an aggregate region grid, optimized for
  scanning and comparison, readable through Life / Energy / Mutation / Stability
  modes.
- **Micro Life Field** — clicking a region opens a close-up that represents the
  region's aggregate signals as a living, animated field.

Two rejected options clarify the choice. Running an actual B3/S23 automaton inside
each region was rejected because the backend holds no binary cell state, and doing so
would invent a second, competing source of truth. A pure particle/swarm animation was
rejected because it would give motion while hiding the birth/death, neighbourhood,
and density ideas that connect Evoverse to its cellular-automata roots.

The accepted model is a **hybrid, sampled micro-life projection**. It is explicitly
*not* canonical backend state; it is a deterministic, sampled visual derived from the
selected region's current data — species share, population, traits, recent events,
and resource/stability fields. It combines the *local emergence* feeling of Conway,
the *smooth density field* feeling of Lenia, and Evoverse's own ecology of resources,
stability, and events. The projection is deterministic — the same region, tick, and
seed can reproduce the same starting field — which keeps it honest and lets it connect
to replay and snapshots later. To avoid misleading users, its copy explains that
population is an aggregate, not an exact count of the agents on screen. A visual
legend maps the encoding — hue to species, drift to mobility, clustering to
cooperation, brightness to energy, a spark to birth, a fade to death, ripples to
events, a red wash to collapse — so the language is learnable rather than decorative.
Crucially, the field tracks a **living population**: as a projection changes, new
agents are *born* and vanished ones *die* through a persistent agent pool, rather than
the whole field being re-seeded on every update.

### Time navigation: the signature capability

Most simulations offer navigation through space. Evoverse's distinguishing bet is
navigation through **time**. The universe map carries a persistent time scrubber:
drag across snapshot frames and the map **redraws itself from historical snapshots**,
mapping each frame's region and species detail back into the same layout the live map
uses. It supports **Era bands**, a **Time Zoom** (recent / wider / full history) that
reframes the axis, a population sparkline, and a cinematic **Replay** that plays the
world forward. A user can enter a region and, in effect, ask to see its past.

This is why determinism and the snapshot spine matter so much: time travel is only
meaningful if the past is stored faithfully and reads back consistently. The current
implementation steps between stored frames; true inter-snapshot interpolation, event
clustering, and full-history paging are identified as future refinements rather than
present claims.

### Phylogeny: history as a branching tree

A species' origins are shown as a **time-axis phylogenetic tree**. The horizontal axis
is the Alpha Age at which a species emerged; the vertical axis is lineage. Each species
becomes a "lifeline," children branch off their parent's lifeline at their own
emergence age, radiation appears as branching, and extinction appears as a branch
fading, going dashed, and being capped. The node set is generated with a **bounded**
strategy — ancestor chain, siblings, and a capped descendant subtree — with a
"showing N of M species" indicator, so the tree stays readable instead of trying to
render the entire lineage graph at once. This is a deliberate replacement of an
earlier single-level graph: the point of the tree is to show *when* and *how* a species
arose, which only a time axis can convey.

### Forecast: deterministic and honestly labeled

Each species carries a **Forecast** surface — extinction risk, dominance probability,
expansion pressure, and mutation volatility — rendered as radial gauges plus a
**population fan chart** with a widening confidence band around a projected median and
a "now" divider between observed and projected. This projection is generated
deterministically from forecast signals; it is *illustrative*, derived from trends and
mutation rates, and it is **not** presented as real AI. Restraint here is a stated
principle: forecast is a legible reading of the simulation's own trajectory, not a
predictive model dressed up as one.

### Spatial fidelity: the hex substrate

The map's spatial model was upgraded from a grid that followed array order to a true
**hexagonal honeycomb** laid out from each region's `x`/`y` coordinates (pointy-top,
odd-r offset). The result is that neighbours on the map are genuinely neighbours in
the model, which matters because migration and event propagation are neighbour-based.
On top of that layout, two ambient signals reinforce the "living world" reading:
**activity waves** ripple outward from regions with recent events to their neighbours
via a multi-source breadth-first ring distance, and the whole map **breathes** at a
rate tied to global stability — calmer when Alpha is stable, with live regions
pulsing individually. All of these motions respect `prefers-reduced-motion` and switch
off when a user asks for reduced motion.

### Reading the language, not the machinery

Across every surface, public language stays in the world's terms — Alpha Age, Era,
species, regions, stability, population, "mutation detected," "region collapsed,"
"species emerged." The first screen is a **Smart Observatory Landing** that shows live
Alpha status, featured Chronicle events, and a mini universe preview rather than a
marketing hero, so the universe's aliveness is the first thing a visitor perceives.

---

## 6. Engineering Approach

### API and worker as separate processes

The backend is a **FastAPI** application and a **separate simulation worker**. They do
not share memory; they share Alpha through **PostgreSQL**. The worker advances Alpha
and writes back the universe, regions, species, populations, events, and active
Catalyst actions; the API refreshes Alpha from PostgreSQL on reads. This split keeps
the simulation's cadence independent of request traffic and lets each side scale and
fail on its own terms.

Because two processes write shared state, writes carry an **optimistic tick check**:
a stale API or worker write fails rather than silently overwriting newer simulation
state. Workers emit **heartbeat records** surfaced through an admin health endpoint,
so the liveness of the background process is observable rather than assumed.

### The BFF and the auth boundary

The frontend is a **Next.js App Router** application, and its relationship to the
backend is mediated by a deliberate boundary. The browser calls **only same-origin
`/api/*` BFF routes**; those routes attach trusted session headers server-side and
forward to the backend. The browser never carries local user ids and never makes
cross-origin calls to the API. This covers observer and catalyst mutations, admin
rule mutations, notification bulk-read, and historical snapshot reads.

Identity is resolved from session/header context. A trusted-header contract
(`x-evoverse-user-id` and its observer/catalyst/admin variants, optionally gated by a
shared secret) lets the BFF speak for an authenticated user, while admin write
endpoints require an active admin role and reject guests with `403`. **Google OAuth**
is wired through the BFF with an HTTP-only session cookie, and a configurable
**local-fallback** mode keeps local development friction-free while a production flag
can require real identity and return `401` when it is absent. The design intent is a
single trusted path into the backend, so that authorization is enforced in one place
rather than trusted from the client.

### Governed, editable rules

Because the world's behaviour lives in a central rules module, that module is exposed
as a **governed admin surface**: read-only rules can be inspected, and edits flow
through **draft → validate → apply → rollback**, with a risky-change preview (collapse,
recovery, extinction thresholds, catalyst quotas, and large swings are flagged and
require explicit confirmation), an audit log, and revision history. Applying a change
hot-reloads the API in place and signals the worker to pick it up, with restart
requirements made visible in the UI. This turns "tuning the simulation" from a code
deployment into an observable, reversible, auditable operation.

### Bounded intervention

The most important design decision about Catalyst effects is that they are **not
global**. A Catalyst acts on a *specific region*; the effect (an energy, mutation, or
resource pulse) is written to the event store, and the simulation processes it over
subsequent ticks. Actions are role-gated, rate-limited per user/action/day, and
protected by per-region cooldowns; accepted actions return result-tracking metadata,
and downstream events can generate notifications. The user is shown that an *influence
was initiated*, never a guaranteed outcome. Global effects would degrade into spam;
regional, simulation-arbitrated effects preserve the observatory's integrity.

### Operations and persistence discipline

Migrations run as ordered SQL files against a `schema_migrations` ledger with
checksums, reporting applied / pending / mismatch state; a heavier migration framework
is intentionally deferred until schema churn justifies it. Observability is built in —
request and error logs, worker lifecycle events, and a product-analytics endpoint — and
surfaced through admin summaries. API errors use a single standard envelope
(`{"error":{"code","message","status"}}`) so failure is as structured as success.
Production hardening — deployment model for the background worker, migration and
recovery playbooks, and a seed/reset safety model — is sequenced *after* the experience
layer, on the explicit principle that a living ecosystem should be proven before its
dashboard is hardened.

---

## 7. Design Principles & Open Questions

A handful of principles recur throughout the project and are worth stating plainly:

- **The simulation keeps authority.** Users observe and, at most, influence. No user
  can create life, invent a species, or reset the world.
- **Aggregate over binary.** Regions carry ecological state, not a single bit, because
  the product must explain *what, where, which, and whether-improving*.
- **Fixed substrate, moving dynamics.** The region grid does not grow; life, resources,
  and stability move across it.
- **Determinism is a feature.** Reproducibility is what makes history, replay, and time
  travel trustworthy.
- **Event and snapshot are distinct.** The log records what happened; snapshots record
  state at a tick. Keeping them separate keeps history unambiguous.
- **The frontend renders; it does not compute.** Critical numbers come from the
  backend.
- **Speak the world's language.** Alpha Age and Era, not ticks and seeds. Forecast is
  labeled as illustrative, never as real AI.
- **Prove aliveness before hardening.** The signature promise is a walkable living
  history; operational polish follows it.

Several decisions remain genuinely open and are tracked as such rather than papered
over:

- **World-age conversion** — how one tick maps to years or eras is undecided. Digest
  cadence and the logarithmic time axis run on placeholder constants until this is
  settled, because the choice is a matter of feel as much as literature.
- **Catalyst access** — currently invite / role-gated, with Google OAuth feeding that
  contract; whether a subscription tier gates it later is unresolved.
- **Real-time cadence** — the target is a 24/7 live universe, with admin-controlled
  batch ticks acceptable during low activity.
- **Render layer** — Canvas 2D plus CSS is sufficient at the current scale, but a
  scrubbable timeline, a branching phylogenetic tree, and thousands of micro agents
  make a future move to PixiJS/WebGL (or a dedicated timeline/tree library) worth
  evaluating.

The north star that orders all of this is deliberately blunt:

> Evoverse should feel like a living artificial ecosystem first, and a report
> dashboard second.

Everything in this document — the aggregate ecology, the bounded loop, the determinism,
the snapshot spine, the macro/micro split, and the walkable history — is in service of
making that first impression true, and of letting a curious observer follow a single
question all the way down: *how did this species come to be here?*
