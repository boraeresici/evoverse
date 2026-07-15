# Evoverse — Correlation Length & Organism Pattern Census

> **Status:** design proposal (not yet implemented). This document specifies a
> deterministic **diagnostic** for `benchmark.py`: a scale-free correlation-length
> measurement over region fluctuations, and an organism-pattern census that
> *captures and counts* recurring motifs in the world. It is a measurement layer,
> not a new simulation rule — it observes the engine, it does not change it.

Like [`CHIRALITY_AND_MIND.md`](CHIRALITY_AND_MIND.md), this uses science as
**orientation, not endorsement**. A scale-free correlation appearing in Evoverse
would show the simulation sits near a *critical point* — it would **not** prove the
model is biologically true. Convergence is a compass, not a certificate (see
[CHIRALITY_AND_MIND §9](CHIRALITY_AND_MIND.md)).

---

## 1. Motivation

Two questions, one answer:

1. **"How effective is the starling scale-free formula for organism formation, and
   can the system reproduce it?"** The Cavagna–Giardina–Parisi result on starling
   flocks (`∑ᵢ uᵢ = 0`, scale-free correlation of velocity *fluctuations*) is **not a
   generative rule** — it is a *diagnostic*. You subtract the collective mode (the
   flock's mean velocity), then measure how far the residual fluctuations stay
   correlated. When that correlation length ξ grows with system size L, the system is
   **scale-free / critical**: information crosses the whole flock regardless of size.

2. **"Can we capture the patterns in organisms and count their recurrences?"** Near a
   critical point, structure becomes *self-similar* — the same motifs recur at every
   scale. So a **pattern census** (capture → canonicalize → count) is the direct,
   empirical companion to ξ. If patterns recur across scales *and* ξ ∝ L, we have
   captured the phenomenon the slide is about.

The single deliverable of this doc is a diagnostic that answers **both** with numbers:

> **A.** `correlation_length(state)` → C(r), ξ, and a scale-free verdict across sizes.
> **B.** `pattern_census(state)` → distinct motifs, their recurrence counts, a
> diversity measure, and a power-law fit on motif sizes.
> **C.** `pattern_triggers(state)` → **which conditions trigger which patterns** —
> a lift table joining each motif to the state (era, region bands, collapse, catalyst)
> it forms under.

Both are **read-only, deterministic, replayable** — the same `(seed, ticks, size)`
always yields the same numbers, so results are comparable across runs and commits.

---

## 2. The physics we are reproducing (the slide, precisely)

The slide shows two panels and one equation:

- **Panel A — full velocities:** every bird's actual velocity `vᵢ` (mostly the shared
  flock motion).
- **Panel B — velocity fluctuations:** `uᵢ = vᵢ − V`, where `V` is the flock mean.
  This is the *interesting* signal — the deviations.
- **The equation** `∫₀ᴸ dr ∑ᵢⱼ uᵢ·uⱼ δ(r − rᵢⱼ) = ∑ᵢⱼ uᵢ·uⱼ = (∑ᵢ uᵢ)·(∑ⱼ uⱼ) = 0`
  just states the **mean-subtraction constraint**: because `uᵢ` are deviations from
  the mean, their total sum is zero. This *forces* the correlation function to cross
  zero at some distance — and that zero-crossing **defines** the correlation length ξ.

The load-bearing distinction for Evoverse:

| | Starling analogue | Evoverse analogue | Regime |
|---|---|---|---|
| **Collective order** | flock flies together | homochirality lock; a species dominating | ordered / super-critical |
| **Critical fluctuations** | scale-free `uᵢ` correlation | scale-free `δφᵢ` correlation | **critical** |

Evoverse's engine today ([engine.py `_advance_chirality`](../backend/app/simulation/engine.py))
is tuned to **lock** (order), like the flock flying together. The slide's phenomenon
lives one notch away, at criticality. **This diagnostic is how we find that notch.**

---

## 3. Part A — Correlation length ξ

### 3.1 The fluctuation field

The world is a `width × height` grid of `Region`s with integer coords `(x, y)`
([seeder.py `_seed_regions`](../backend/app/simulation/seeder.py)). Pick a scalar
field φ per region; define the fluctuation exactly as the slide does — subtract the
mean over **non-collapsed** regions (collapsed regions are "dead birds", excluded):

```
𝓡      = { region : not region.collapsed }
φ̄      = mean(φ(region) for region in 𝓡)
δφ(i)  = φ(i) − φ̄            # ∑ δφ = 0 by construction — the slide's constraint
```

Candidate fields, in preference order (why):

| Field | Source | Note |
|-------|--------|------|
| `stability` | `region.stability` | continuous, never saturates — **best default** |
| `energy_level` | `region.energy_level` | continuous, catalyst-perturbed |
| `resource_density` | `region.resource_density` | continuous, has forced shocks |
| `growth_rate` | mean of region's populations' `growth_rate` | the closest analogue to a *velocity* (rate of change) |
| `chirality_ee` | `region.chirality_ee` | **saturates to ±1** once locked → poor for ξ in the ordered phase; useful only *during* symmetry breaking |

`growth_rate` is conceptually the tightest match to the starling `vᵢ` (a rate/flow),
so the diagnostic computes ξ for **each** field and reports them side by side.

### 3.2 The correlation function C(r)

Discrete lattice version of the slide's integrand. `d(i, j)` is the distance metric —
default **Manhattan**, matching the 4-neighbour coupling the engine actually uses
([engine.py avalanche step](../backend/app/simulation/engine.py)); Euclidean is a flag.

```
        ∑_{i≠j}  δφ(i)·δφ(j) · 1[d(i,j) = r]
C(r) =  ───────────────────────────────────
             ∑_{i≠j}  1[d(i,j) = r]
```

Normalise so `C(0) ≡ 1` by dividing through by the variance
`c₀ = mean(δφ(i)²)`. Then:

- `C(r) > 0` at small r → nearby regions fluctuate **together**.
- `C(r)` crosses zero at `r = ξ` → the correlation length (guaranteed to exist by
  `∑ δφ = 0`).
- **Cumulative correlation** `Q(r) = ∑_{s≤r} (stuff)` gives a smoother ξ estimate;
  we report ξ as the linear-interpolated **first zero-crossing** of C(r).

### 3.3 The scale-free test (the actual answer to "yakalayabilir miyiz?")

A single ξ means nothing on its own. Scale-free = **ξ scales with system size**. Run
the *same seed/ticks* at a ladder of sizes and inspect how ξ moves:

```
sizes = [(8,6), (12,9), (16,12), (24,18), (32,24)]   # L = max(width,height)
for (w,h) in sizes:
    state = seed_alpha(seed, width=w, height=h); advance(state, ticks)
    ξ(L)  = correlation_length(state).xi
```

Verdicts:

| Observation | Regime | Meaning |
|-------------|--------|---------|
| `ξ ≈ const` (independent of L) | **sub-critical / disordered** | fixed patch size; no long-range order |
| `ξ ≈ L/2`, and `C(r)` curves **collapse** onto one curve vs `r/L` | **critical — scale-free** ✅ | the slide's phenomenon: correlation spans the whole world at every size |
| `ξ` saturates at L then `C(r)` stays positive (never crosses) | **super-critical / ordered** | one domain; the "flock flies together" / homochirality-locked case |

The diagnostic returns `xi_over_L` for each size and a **`data_collapse_error`**
(RMS spread of the `C(r/L)` curves); low spread + `xi_over_L ≈ const` ⇒ scale-free.
This is a *number*, so criticality-tuning of `amplify_k` / `avalanche_bleed` can be
scripted against it.

---

## 4. Part B — Organism pattern census (capture **and** count)

Criticality's fingerprint is **self-similar, recurring structure**. This part
captures motifs at four levels, canonicalises each to a hashable key, and counts
recurrences with a `collections.Counter` — fully deterministic. Every level reports:
`distinct` (how many kinds), `top` (most frequent motifs with counts), `entropy`
(Shannon diversity) and `effective_count` (`2^entropy`, "how many motifs effectively
exist").

### 4.1 Morphotype motifs — *convergent evolution*, counted

Quantise each species' trait vector into bins (default 0.1 → 11 levels per trait) to
get a **morphotype signature**:

```
sig = ( round10(efficiency), round10(adaptation), round10(cooperation),
        round10(mobility),  round10(resilience) )
```

Count, per morphotype: number of distinct species, number of *independent lineages*
(distinct root ancestors via `parent_species_id`), and total population carrying it.

> **Convergence index** = (# morphotypes reached by ≥2 independent lineages) /
> (# distinct morphotypes). High ⇒ the world keeps re-discovering the same body plan
> from unrelated ancestors — recurrence in trait space, the biology reading of
> "the same pattern at every scale."

### 4.2 Spatial configuration motifs — patterns in space

For each region, take `dominant_species_id` and the multiset of its neighbours'
dominant species, **relabelled canonically** (self = `0`, "same as self", distinct
neighbours by first appearance) so the motif is translation- and identity-invariant:

```
region dominant = A, neighbours = {A, A, B, C}  →  key = (0, [0,0,1,2])
```

Count recurring local tilings: solid domains `(0,[0,0,0,0])`, domain walls
`(0,[0,0,1,1])`, lone cells `(0,[1,2,3,4])`. This is the direct analogue of reading
structure off panels A/B — **where** organisms cluster, and how those clusters repeat.

### 4.3 Domain-size distribution — the scale-free link between A and B

Flood-fill connected regions sharing the same `dominant_species_id` into **domains**;
histogram their sizes. Near criticality this histogram is a **power law**
`P(s) ∝ s^(−τ)` (like avalanche sizes). The diagnostic fits τ (log-log least squares)
and reports `r_squared`. **A power-law domain-size distribution *is* the pattern-level
signature of the same criticality that ξ ∝ L measures at the field level** — the two
parts corroborate each other.

### 4.4 Lineage-shape & life-cycle motifs — patterns in time

- **Phylogeny motifs:** from `parent_species_id`, extract each species' local branching
  shape (child count, whether children went extinct) and count recurring subtrees.
- **Event n-grams:** per species, the ordered sequence of its `EventType`s
  (`EMERGED → DECLINED → EXTINCT`, `EMERGED → DOMINANT → …`); count recurring
  life-cycle n-grams (default n = 3). Recurring life-cycles = temporal patterns.

---

## 5. Part C — Which conditions trigger which patterns

Part B counts *what* recurs. This part answers *when and why* — the **condition →
pattern** association ("belirli durumlarda oluşan belirli patternler"). It turns the
census into rule-like readings: *"this motif appears mostly at collapsed boundaries,
in the Stabilization era, under a resource burst."*

### 5.1 The condition vector

For any pattern instance, snapshot the **quantised** state co-located with it — this
is the "durum" the pattern formed under:

```
condition = (
    era,                                   # GENESIS / EXPANSION / STABILIZATION / INTELLIGENCE
    band(region.stability),                # low / mid / high  (or 0.1 bins)
    band(region.resource_density),
    band(region.energy_level),
    region.collapsed,                      # bool
    neighbour_collapsed_count,             # 0..4  — "at a dead edge"
    sign(region.chirality_ee), region.chirality_locked,
    active_catalyst_types(region),         # {} / {RESOURCE_BURST} / …
    tick_band,                             # coarse time window
)
```

### 5.2 Two capture modes

- **Static co-location (final state, zero extra cost).** Spatial motifs and domains
  already sit on regions — stamp each instance with its region's condition vector and
  correlate immediately.
- **Trace mode (`--trace K`, deterministic replay).** Re-advance sampling every `K`
  ticks, **diff** the census, and stamp each *newly appeared* motif with the current
  conditions — i.e. its **emergence** conditions, not just its final ones. For
  lineage/morphotype motifs, join the species' `SPECIES_EMERGED` / `_DECLINED` /
  `_EXTINCT` events (which already carry `region_id`, `tick`, `payload`) to the
  origin-region conditions at that tick. Replay stays deterministic, so a traced run
  is as reproducible as a static one — **and the engine is never touched** (we
  re-derive by replay rather than storing per-tick history).

### 5.3 Association measure (lift)

For motif `m` and condition `c`, over `N` sampled instances:

```
lift(m, c) = P(m | c) / P(m) = [ count(m ∧ c)/count(c) ] / [ count(m)/N ]
```

`lift > 1` ⇒ condition `c` **triggers** `m` (over-represented). Always report
`support = count(m ∧ c)` alongside, so a rare-but-high-lift coincidence is visibly
weak. Also emit each motif's **modal condition** (its single strongest trigger) and
each condition's **top-triggered motifs**. Pure counts ⇒ deterministic.

> **Honesty note:** lift is *association within the model*, not biological causation;
> and with few species the supports are small. Reporting `support` keeps weak
> associations from reading as laws.

### 5.4 API & output

```python
def condition_vector(state, region) -> tuple: ...           # the quantised snapshot
def pattern_triggers(state) -> dict:                         # static co-location
def pattern_triggers_traced(seed, ticks, *, step) -> dict:  # trace / emergence mode
```

```jsonc
"triggers": {
  "mode": "static",                       // or "traced"
  "table": [
    { "pattern": "spatial:0|0,0,1,1", "condition": "collapsed_boundary|era=STABILIZATION",
      "lift": 3.4, "support": 11, "pGivenC": 0.28 }
  ],
  "conditionProfiles": {                  // each top motif's modal condition
    "spatial:0|0,0,0,0": { "era": "STABILIZATION", "stabilityBand": "high", "catalyst": "none" }
  },
  "topByCondition": {                     // each condition's most-triggered motifs
    "resource_burst_active": [ {"pattern":"morphotype:high-mobility","lift":2.1,"support":6} ]
  }
}
```

The `table` is sorted by `lift · log(support)` so strong **and** well-supported
triggers rank first. This is the layer that reads as *"specific patterns forming
under specific conditions,"* captured and counted.

---

## 6. API & wiring

All additions live in [`benchmark.py`](../backend/app/simulation/benchmark.py); no
engine or domain changes. Pure functions over an `AlphaState`:

```python
def correlation_field(state, field: str, *, metric: str = "manhattan") -> dict:
    """C(r) table, c0 variance, and ξ (first zero-crossing) for one scalar field."""

def correlation_length(state, *, fields=DEFAULT_FIELDS, metric="manhattan") -> dict:
    """ξ + C(r) for every field in `fields`."""

def scale_free_scan(seed, ticks, *, sizes, field="stability") -> dict:
    """Re-seed & advance at each (w,h); return ξ(L), xi_over_L, data_collapse_error,
       and a verdict in {sub_critical, critical, super_critical}."""

def pattern_census(state) -> dict:
    """morphotypes, spatial_motifs, domain_size_powerlaw, lineage_motifs, event_ngrams;
       each with distinct / top / entropy / effective_count (+ convergence_index,
       + powerlaw {tau, r_squared})."""
```

CLI (extends `main()` — off by default so the fast benchmark stays fast):

```
python -m app.simulation.benchmark --correlation            # ξ for the final state
python -m app.simulation.benchmark --patterns               # pattern census
python -m app.simulation.benchmark --scale-free --sizes 8x6,12x9,16x12,24x18
python -m app.simulation.benchmark --patterns --json        # machine-readable
```

**Output schema** (new top-level keys; existing keys untouched so nothing that reads
the report breaks):

```jsonc
{
  "correlation": {
    "stability": { "xi": 4.7, "c0": 0.012, "curve": [[1,0.63],[2,0.29],[3,0.02],[4,-0.18]] },
    "growth_rate": { "xi": 2.1, ... }
  },
  "scaleFree": {
    "field": "stability",
    "points": [ {"L":6,"xi":2.9,"xiOverL":0.48}, {"L":9,"xi":4.7,"xiOverL":0.52}, ... ],
    "dataCollapseError": 0.031,
    "verdict": "critical"
  },
  "patterns": {
    "morphotypes":   { "distinct": 41, "convergenceIndex": 0.17, "effectiveCount": 22.4,
                       "top": [ {"sig":[0.6,0.5,0.4,0.3,0.7], "species":6, "lineages":3, "population":184000} ] },
    "spatialMotifs": { "distinct": 12, "top": [ {"key":"0|0,0,0,0", "count":37}, {"key":"0|0,0,1,1","count":21} ] },
    "domainSizePowerLaw": { "tau": 1.9, "rSquared": 0.94, "domains": 28 },
    "lineageMotifs": { "distinct": 9,  "top": [...] },
    "eventNgrams":   { "distinct": 15, "top": [ {"ngram":"SPECIES_EMERGED>SPECIES_DECLINED>SPECIES_EXTINCT","count":8} ] }
  }
}
```

### 6.1 Determinism

- No new randomness — every function is a pure fold over `state`. Same
  `(seed, ticks, size)` ⇒ identical output. Verified by hashing `patterns` +
  `correlation` and asserting stability across two runs, alongside the existing
  `determinism_signature`.
- Iterate `state.regions` / `state.species` / `state.populations` in **sorted id
  order** everywhere (as the existing report already does) so Counters and curves are
  order-independent.
- `scale_free_scan` re-seeds with the *same* seed at each size; only `width/height`
  vary. (`seed_alpha` already takes `width`, `height`.)

---

## 7. Non-goals & open questions

- **Non-goal:** claiming an observed power law / scale-free ξ proves Evoverse is
  biologically correct. It measures **criticality and self-similarity of the model**,
  full stop (see [CHIRALITY_AND_MIND §9](CHIRALITY_AND_MIND.md)).
- **Non-goal:** changing engine dynamics. This is observation only. Tuning toward
  criticality (`amplify_k`, `avalanche_bleed`, region reversion factors) is a
  *separate* follow-up that would *use* these numbers as its objective.
- **Open:** best field for ξ — `stability` (always continuous) vs `growth_rate`
  (truest velocity-analogue but zero for extinct/idle populations). Report both; pick
  after first runs.
- **Open:** distance metric — Manhattan matches the 4-neighbour coupling, but the
  Organism Lens design assumes hex; if the map goes hex, add the hex metric here too.
- **Open:** morphotype bin width (0.1) and event n-gram length (3) are first guesses;
  expose as function args and tune against the 10k-tick world.
- **Open (triggers):** trace sampling step `K` (temporal granularity vs replay cost);
  condition-band cutoffs (low/mid/high thresholds); and whether to eventually store a
  lightweight per-tick condition ring-buffer in the engine instead of re-deriving by
  replay (replay keeps the engine untouched — **preferred** until cost forces it).

---

## 8. Build order (slices)

1. **`correlation_field` + `correlation_length`** on the final state, `--correlation`
   CLI, C(r)/ξ in the report. Golden-value test on the default seed.
2. **`scale_free_scan`** + `--scale-free --sizes …`, the verdict, and the data-collapse
   error. This is the slice that literally answers *"yakalayabilir miyiz?"*.
3. **`pattern_census` levels 4.1–4.2** (morphotypes + spatial motifs) with counts,
   entropy, convergence index.
4. **`domain_size_powerlaw` (4.3)** — the scale-free bridge between Part A and Part B.
5. **Lineage & event motifs (4.4)**, then fold `patterns`/`correlation` hashes into the
   determinism guard.
6. **Conditional triggers (Part C)** — `pattern_triggers` (static co-location) first,
   then `pattern_triggers_traced` (`--trace K`) for emergence conditions and the lift
   table. This is the slice that turns the census into *condition → pattern* readings.
