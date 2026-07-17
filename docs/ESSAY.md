# Evoverse: Not Creating a World, but Witnessing One

### An artificial-life observatory, its physics, and the instruments it built to tell itself it hasn't succeeded yet

*Bora ERESICI (StudioBinary) · Planned and built 2025–2026 · v0.4.0*

---

## Prologue: the number that wasn't there

Somewhere in this repository there is a sweep that runs eight universes, turns off a single parameter, and reports that none of them earn the right to life.

That sentence is either marketing or a measurement, and the difference is the whole subject of this essay.

It is a measurement. You can run it:

```
PYTHONPATH=backend python -m app.simulation.sweep --param field_strength
```

Every number in this essay was produced by running the repository at the commit it describes, not quoted from an earlier document. That distinction matters more than it should, and this essay is where it earns its keep: **one of the numbers came back different.** The project's published verdict about its own criticality does not reproduce — and the code's answer is more conservative than the sentence written about it (§4).

That is not an embarrassment. It is the system working. This project has already caught its own documentation lying once, and the mechanism it built to catch it is one of its better ideas. This essay is that mechanism, run once more, by hand.

---

## 1. The origin: a product defined by three negations

Evoverse did not begin with a thesis about the origin of life. It began with a complaint about a genre.

The earliest planning notes — a raw thinking transcript, not a specification — arrive at the project's identity mid-sentence: *at this point the product is no longer a game, no longer a sandbox, no longer a Conway clone; it becomes a **Persistent Artificial Life Observatory***. The hinge is the phrase "at this point." The framing arrived as a realization, not a premise. The project knew what it wasn't before it had a name for what it was.

The formalized version diagnoses an entire genre in two lines. Artificial-life simulations, it argues, mostly sit at one of two extremes: either they hand the player so much control that the simulation's independence collapses, or they are pure technical visualization and give nobody a reason to come back. Evoverse is defined as the middle term.

Two horns. Too much agency kills the world's autonomy; pure visualization kills the reason to look.

And, crucially, the founding risk was never technical. The notes are blunt about it: *the biggest risk is not technical risk — it is **interest risk**. Why should the user come back?*

Hold that. It was written by someone worrying about retention. Its descendant is a physics measurement. That transformation is the story of this project.

### The Conway debt, accounted for

Most projects in this space gesture at Conway's *Game of Life* and move on. Evoverse wrote a document that scores its own derivativeness:

| Layer | Self-assessed link |
|---|---|
| Direct algorithmic link | 32/100 |
| Simulation approach link | 72/100 |
| Product lineage | 56/100 |

Then it published those numbers as public product copy. Read them correctly: these are scores of *linkage*, so 32/100 says the algorithmic debt to Conway is small, while 72/100 concedes that the simulation *approach* is substantially inherited. A project that volunteers "our method is 72% someone else's idea" as marketing is doing something unusual — treating lineage as a debt to be measured rather than a claim to be made.

The positioning that came out of it:

> Evoverse starts from the spirit of Conway's Game of Life, then expands it into a persistent artificial-life observatory with species, regions, resources, interventions, and historical reports.

And the load-bearing design argument for *why not binary cells*: they are excellent for pure emergence, but they cannot answer "why did this happen, where, which species was affected, is it better than before?" So each grid cell was raised into a **region aggregate** — energy, resources, stability, a dominant species, a population.

This is the first of several places where a product constraint turned out to be a scientific commitment in disguise. Aggregate regions are why the world has thermodynamics instead of rules.

---

## 2. What the world actually is

Alpha is a **12 × 9 grid = 108 regions**, ticking continuously, seeded at `4211`.

Two properties are load-bearing and everything else follows:

**Determinism.** `(seed, rules, tick)` always yields the same universe. Every random draw is hash-seeded — `stable_rng` SHA-256s the key `seed:label:tick:id` and seeds a fresh `random.Random` from the digest. There is no wall clock in the step and no global RNG stream. This is not hygiene; it is the precondition for everything else in this essay. You cannot replay, forecast, or *measure* a world that cannot be re-run.

**Event sourcing.** The chronicle is append-only; every entity carries provenance. "Why did this region collapse?" is a question with an answer you can click.

A single tick runs an ordered pipeline — the order is load-bearing, because each stage reads what the previous stage wrote:

```
consumption pre-pass → region drift (energy/resource/stability)
  → resource-shift reporting → collapse/recovery hysteresis
  → chirality (bifurcation → lock → avalanche → lineage adoption → aggregation)
  → populations (habitat fit → heterochiral tax → growth → decline → migration)
  → scripted collapse → speciation → species status
  → dominance → universe stability → era gate → catalyst expiry
```

Populations are **species-region aggregates**, not individuals. A region reading `26,421 population` does not contain 26,421 simulated organisms; it contains a number that grows, declines, migrates, and mutates. This was a Phase-1 performance decision. It is also the reason the project can say honest things about ecology and cannot yet say anything about individuals — a limit we will return to.

### The catalyst: influence without determination

The third user role can nudge a region — an energy pulse, a mutation pulse, a resource burst — with daily quotas of 3, 1, and 1 respectively. Those three integers were written in the earliest product sketch and ship untouched in `rules.py` today.

What makes it interesting is the mechanism. A catalyst action **does not mutate state**. It deposits a *bias* that the region's normal tick consumes as an input to ordinary drift, at strength `0.18` over `8` ticks. The engine is free to do nothing with it.

The planning notes put it exactly: the user creates an effect on a region, a mutation wave may spread — *but the simulation decides what will happen*.

The design goal is stated as an emotional contract, and it is the sharpest line in the planning docs: **the user should feel they touched the universe, and understand that control remained with the simulation.**

This is the answer to the first horn of the founding complaint. You can act on the world without becoming a god of it, because the mechanism of your action is *a thumb on a scale the engine may ignore*. The non-determination is mechanical, not rhetorical.

---

## 3. The scientific turn: homochirality

Version 0.4.0 is where a product acquired a physics.

### The question

Every amino acid in every living thing on Earth is left-handed. Every sugar is right-handed. The chemistry does not require this — synthesize amino acids abiotically and you get a 50/50 racemic mixture. Yet life runs, universally, on one hand.

This is **homochirality**, and it is one of the genuinely open problems in origin-of-life research. Its significance is not aesthetic: a racemic soup cannot build a consistent polymer. Mixed-handed monomers produce chains that cannot fold reproducibly. **Without symmetry breaking, there is no reliable information carrier — and therefore no heredity.**

Evoverse's thesis, stated plainly in its design doc:

> Homochirality is the symmetry breaking that lets information exist at all; applied to molecules it produces life, applied to a lineage's internal model it produces thought. Same math, two tiers.

The first tier (T1) is implemented. The second (T2, "mind") is not — and the honesty about that gap is a subject in itself (§6).

### The mechanism

Each region carries an **enantiomeric excess** `ee ∈ [-1, 1]`: `0` is racemic, `±1` is fully single-handed. Per tick:

```
ee ← ee + (amplify_k · ee − amplify_k · ee³) − racemization_rate · ee
       + field_strength · direction
       + noise · (1 − |ee|)
```

Strip the field and noise and this is the **normal form of a pitchfork bifurcation** with control parameter:

```
μ = amplify_k − racemization_rate
```

At `μ ≤ 0` the racemic state `ee = 0` is stable and no amount of time produces a hand. At `μ > 0` it destabilizes and the system falls to one of two symmetric fixed points:

```
ee* = √(1 − racemization_rate / amplify_k)
```

This is not an analogy to autocatalysis — it is the standard reduced description of it (the Frank model's mathematical skeleton). The shipped constants are `amplify_k = 0.06`, `racemization_rate = 0.008`, so `μ = 0.052` and `ee* = 0.931`.

Three details are worth pausing on, because each encodes a physical commitment:

**Noise is damped by `(1 − |ee|)`; the field is not.** Noise is a property of the region's own racemic jitter — a committed region has less of it. The field is external and does not care how committed you are. This asymmetry is the whole reason the field wins.

**The lock is irreversible.** When `|ee| ≥ 0.9` the region latches to exactly `±1` and stops evolving. Locked regions skip the bifurcation step entirely, so racemization never taxes a latched region.

**A lineage's hand is inherited, not re-derived.** A species takes its hand from its origin region when that region latches — which, for early species, is many ticks after they emerge — and children take theirs from the parent, not from the ground they are born on. A mismatched population pays a growth penalty; past a lethal load it dies. This is the "chiral central dogma": one-way inheritance, with one deliberate leak — speciation carries a **1% flip chance**, so the hand is heritable rather than absolutely conserved. Without that leak the system could never explore the other branch at all.

### The first result: locking is not enough

Here is where the project found something.

Run the world with the field turned off (`field_strength = 0`). Every region still locks — the bifurcation is intact, autocatalysis works, each region commits to a hand. **And the universe is correctly denied life.**

I ran this. Eight seeds, 600 ticks, freshly generated:

| `field_strength` | single global hand | life earned | mean domains | mean `H` (95% CI) | mean lock tick |
|---:|---:|---:|---:|---|---:|
| **0** | **0/8** | **0/8** | 4.4 | 0.215 [0.108, 0.321] | 167 |
| 0.001 | 2/8 | 7/8 | 2.3 | 0.923 [0.865, 0.981] | 115 |
| 0.002 | **8/8** | 8/8 | 1.0 | 1.000 [1.000, 1.000] | 92 |
| 0.005 *(shipped)* | 8/8 | 8/8 | 1.0 | 1.000 [1.000, 1.000] | 64 |
| 0.01 | 8/8 | 8/8 | 1.0 | 1.000 [1.000, 1.000] | 45 |

Without the field, essentially every viable region still locks — 107.6 of 108 on average, the remainder having collapsed — and the map fragments into **~4.4 opposing domains**: locked, locally pure, globally racemic. A **chiral glass**.

This is why the metric had to be corrected mid-flight, and it is the most important epistemic move in the codebase. The universe's maturity metric is:

```
homochirality_index = |mean ee|        ← global agreement
local_order_index   =  mean |ee|       ← local commitment
```

`mean |ee|` reads **1.0** for a chiral glass — every region perfectly pure, none agreeing. That number is real and it means nothing. Earlier versions gated the Era progression on it, and handed the Stabilization Era to globally racemic universes at tick 68.

> **The universe scope is `|mean ee|`, not `mean |ee|` — and the difference is the whole subsystem.**

Life's homochirality is *global*. All of it runs on one hand. So the gate must be global. And `mean |ee|` was kept — renamed `local_order_index` — because the gap between the two *is* the domain problem, and `domain_count` names it directly.

The lesson generalizes past this project: **a metric that cannot fail is not a measurement.** The field-off universe is the control experiment, and the project ran it on itself.

### The second result: the latch cliff and critical slowing down

Sweeping racemization instead, at the shipped field strength:

| `racemization_rate` | single hand | life earned | locked regions | mean `H` | mean lock tick |
|---:|---:|---:|---:|---:|---:|
| 0 | 8/8 | 8/8 | 107.6 | 1.000 | 58 |
| 0.008 *(shipped)* | 8/8 | 8/8 | 107.6 | 1.000 | 64 |
| 0.012 | 8/8 | 8/8 | 107.6 | 1.000 | 69 |
| 0.016 | 8/8 | 8/8 | 107.6 | 1.000 | 81 |
| **0.020** | 0/8 | **8/8** | **0** | 0.841 | **never** |
| 0.030 | 3/8 | 0/8 | 0 | 0.772 | never |
| 0.060 | 8/8 | 0/8 | 0 | 0.436 | never |
| 0.080 | 8/8 | 0/8 | 0 | 0.218 | never |

Two things here.

**The lock tick climbs and then diverges**: 58 → 64 → 69 → 81 → never. The world does not stop committing at 0.019 and start at 0.020. It takes longer, and longer, and then it doesn't. The transition is continuous — the world approaches an absorbing barrier ever more slowly as the fixed point sinks toward it, and then never reaches it. (The project's own commit log calls this critical slowing down. That is loose: the pitchfork's critical point sits at `racemization = amplify_k = 0.06`, and `μ = 0.04` at the cliff, so this is slowing near the *latch*, not near the *bifurcation*. The phenomenology is the same shape; the mechanism is a threshold, not a symmetry breaking. Worth naming precisely, because §3's own punchline is that the latch, not `μ`, is the operative cliff.)

**Row 0.020 is the interesting one.** At `racemization_rate = 0.020` the no-field fixed point is:

```
ee* = √(1 − 0.020/0.06) = 0.816
```

Below the lock threshold `0.9` — so nothing latches. Above the life gate `0.8` — so the Era gate grants life. Measured: `H = 0.841`, life earned 8/8, locked regions **0**.

The arithmetic gives the *direction*, not the location, and it is worth being precise about why — this is the kind of detail an essay is tempted to smooth over. The same formula puts `ee* = 0.894` at racemization 0.012 and `0.856` at 0.016. Both are below the 0.9 threshold, and both nonetheless latch 107.6/108 regions. The naive fixed point mispredicts two rows of my own table.

The reason is in the code's own comments: the latch is an **absorbing barrier**, and noise carries regions over a fixed point that sits below it. Once over, they never come back. So the real cliff is measured at ~0.018 rather than derived, and the closed form is a lower bound on where committing becomes impossible, not a predictor of where it stops happening. The repository knows this and says so; a validator shipping the naive criterion would false-warn at exactly those two rows.

**Life is granted to a universe where nothing has committed to a hand.** The docs call this the **hollow** phase, and it is the project's sharpest self-criticism: the operative cliff is not `μ`, it is the latch, and there is a window where the metric says yes and the physics says nothing happened.

### The phase diagram

Putting both axes together — 8 seeds per cell, 600 ticks, 108 regions, freshly run:

```
                     field_strength →
              0.0   0.001  0.002  0.005   0.01
      0.0      G      G     g?      H      H
    0.008      G     g?      H      H      H
 ↓  0.016      .      .      .      H      H
 r   0.020     .      .      .      o      H
 a   0.030     .      .      .      .      o
 c   0.060     .      .      .      .      .

  H = homochiral    G = glass (locked, many domains)
  o = hollow (life granted, nothing latched)
  . = racemic
  lowercase + ? = ensemble split — a boundary cell, not a verdict
```

Four phases, all real, all reachable. Read the diagram as an argument:

- **Bottom-left (racemic):** racemization beats the gain. Nothing happens. This is `μ ≤ 0` territory and its neighbourhood.
- **Top-left (glass):** the gain wins locally, but with no field every region picks its own hand. Locked, ordered, globally meaningless. *Autocatalysis alone is not enough.*
- **Right (homochiral):** the field breaks the tie globally. One hand everywhere. This is the phase Earth is in — though not necessarily by this mechanism; see below.
- **The `o` sliver:** hollow. The gate fires on a world that never committed.

Note the row at `racemization = 0.016`: `. . . H H`. Racemic at low field, homochiral at high field. **The field does not merely choose the hand — it extends the region of parameter space where a hand is possible at all.** That is a real, load-bearing result and it falls straight out of the two mechanisms interacting.

Note also that the boundary cells are marked lowercase-with-`?` where the ensemble split. The instrument refuses to render a verdict where its eight seeds disagreed. This is not decoration; see §5.

### What this does and does not claim

It does **not** claim to explain terrestrial homochirality. The field here is an abstract global bias, not a specific physical mechanism; real candidates (circularly polarized light, parity violation, magnetized mineral surfaces) are quantitatively vastly weaker and the gap between "a bias exists" and "this bias suffices" is exactly where the real science lives.

What it claims is narrower and defensible: **in a system with autocatalytic amplification, racemization, and spatial coupling, local symmetry breaking is insufficient for global homochirality, and a weak global bias is sufficient to produce it.** That is a statement about a class of models, it is measured, it is reproducible, and it is falsifiable — turn the field off and count the domains.

---

## 4. The second scientific question: is the world alive enough?

Recall the worry from the planning notes: *the universe may end up either too stable or too chaotic.* A product manager's anxiety about boredom, filed under risks, with mitigations about event-frequency target ranges.

There is a formal name for the line between dead and noise: **criticality**. And there is a real measurement, borrowed from an unlikely place.

### Starlings

Cavagna, Giardina, Parisi and colleagues studied flocks of starlings and asked how far one bird's deviation from the flock's mean velocity correlates with another's. They found the **correlation length ξ scales with flock size L** — a flock of any size is correlated across its whole extent. Scale-free behaviour. The flock has no characteristic length; it sits at a critical point.

Evoverse computes exactly this diagnostic on region fields:

1. Subtract the mean: `δφ(i) = φ(i) − mean(φ)`.
2. Correlate all region pairs, bucketed by integer lattice distance.
3. Normalize by `c₀ = Σδφ²/n`, so `C(0) = 1` by construction.
4. **ξ = the first zero-crossing of `C(r)`**, linearly interpolated.
5. Repeat across world sizes `12×9 → 24×18` and regress ξ on L.

It runs over four fields — `stability`, `energy_level`, `resource_density`, `growth_rate` — and the last is specially justified as "the closest analogue to a starling's *velocity* (a rate of change)," since the others are levels rather than rates. The scan reported below uses `stability`, the default.

### The sum rule, and a function that refuses to lie

Here is the detail that tells you what kind of codebase this is.

Because `Σδφ = 0` by construction, the identity `Σ_{i<j} δφᵢδφⱼ = −n·c₀/2` is **strictly negative**. Therefore *some* `C(r)` must be negative, and a zero crossing always exists. "The curve never crossed" is not a physical state — it is a bug.

So the code raises:

```python
raise ValueError(
    "C(r) never crossed zero, which the sum rule forbids for a varying field — "
    "the fluctuation field is not mean-centred"
)
```

And a test re-derives `−n·c₀/2` independently and asserts relative error `< 1e-9` for every field. The measurement is pinned to the theory that justifies it.

### The verdict the project published about itself

The project's public claim, in its own words:

> The measured verdict on the current engine tuning is `sub_critical` (short-range correlation) — **an honest "not scale-free in this regime", not biological validation.**

The project built the instrument that told it it hasn't succeeded yet, and shipped the instrument anyway. That is the sentence I would have put on the tin.

### The verdict I actually measured

Then I ran it — at the worker's exact default configuration (2000 ticks, 8 consecutive seeds from 4211, the `stability` field, manhattan metric, sizes 12×9 → 24×18):

| L | world | ξ | ξ/L | seeds with floored ξ |
|---:|---|---:|---:|---:|
| 12 | 12×9 | 2.19 | 0.183 | 4/8 |
| 16 | 16×12 | 1.02 | 0.064 | **7/8** |
| 20 | 20×15 | 1.56 | 0.078 | **5/8** |
| 24 | 24×18 | 1.90 | 0.079 | 3/8 |

```
verdict:  underpowered
slope:    -0.0083   95% CI [-0.1205, 0.1039]
collapse: 0.0238    seed noise: 0.0238    ratio: 1.00
```

**Not `sub_critical`. `underpowered`** — a label that did not exist when the `sub_critical` claim was written.

That last clause matters, and it stops this from being a gotcha. The changelog entry that announced `sub_critical` lists the enum as `critical`/`sub_critical`/`super_critical`: it predates both the seed ensemble *and* the `underpowered` verdict. So this is not a number that drifted at a fixed configuration. It is a verdict issued by an instrument that has since been rebuilt to be stricter, and never re-issued.

The repository currently says three different things about this one measurement. The changelog says `sub_critical`. The most recent commit says *"Both fields are flat; the scan's `sub_critical` verdict is honest."* And the scan itself, run at the worker's defaults today, says `underpowered`. All three were written by people looking carefully. None of them is lying. **They disagree because nothing re-runs the scan and compares it to the sentence.**

Two of the four rungs resolved ξ only as an upper bound — the correlation length sits at or below what the lattice can resolve, 1–2 cells across a world 24 cells wide. The verdict short-circuits *before the slope is ever read*, exactly as designed: fit a slope through mostly-bounds and the slope is a bound too.

There is also a physical reading, and it is more useful than the verdict. ξ/L falls from 0.18 to ~0.08 and then stops falling; ξ itself hovers between 1 and 2 cells regardless of world size. That is not a world hovering near a critical point — it is a world whose correlations are essentially local, measured by an instrument whose smallest meaningful unit is one cell. **The scan is not underpowered by accident; it is underpowered because the thing it is measuring is smaller than the ruler.** Widening the size ladder will not fix that. Tuning the engine toward longer-range coupling might.

The difference between the two verdicts is not pedantic. `sub_critical` says *we measured short-range correlation.* `underpowered` says *we could not resolve ξ well enough to say anything at all.* The instrument, running today, is more humble than the claim published about it.

Nor is this a discovery on my part — which is itself the point. The project's own doc already recorded that single-seed scans were a coin flip: *"12 consecutive seeds returned `underpowered` ×7, `sub_critical` ×4, `intermediate` ×1."* `underpowered` was already the most common answer. The ensemble was supposed to settle the coin flip. Measured today, it settles it toward the answer the doc had already seen most often, and the sentence out front never caught up.

So the honest headline is one notch weaker than the advertised one, and one notch more interesting. The boredom risk grew up into a physics measurement, and the physics said: *the question is not resolved at this resolution.*

---

## 5. The epistemics: a measurement layer written against itself

If Evoverse has a genuinely novel contribution, it is not the chirality model. It is the discipline around the numbers. This section is the one I would ask a skeptical reader to check first.

### It refuses to conclude

- **One seed cannot be critical.** With `n = 1`, the spread function returns `sd = None`, `se = None`, and the confidence interval degenerates to the point itself. The docstring: *"That is the honest rendering of a single run — a number carrying no claim."*
- **`underpowered`** short-circuits *before the slope is ever read*, if half the rungs have a floored ξ. *"Fit a slope through mostly-bounds and the slope is a bound too, which is how a run that resolved nothing still walks away labelled 'sub critical'."*
- **`inconclusive`** when the 95% CI straddles a threshold. *"The gates read the 95% CI, not the point estimate… an interval straddling one is `inconclusive` — the run happened and did not resolve the question, which is a thing a point estimate can never say."*
- **`degenerate`** — *"ξ is meaningless, not zero."*
- **Curve collapse returns False on None** — *"unanswerable, rather than passed by default."*
- **Pair counts ship with the curve**, because *"without them a reader cannot tell the measured span from the tail, where a single product masquerades as a correlation."*

### It deletes claims it cannot support

Two labels were removed, and the removals are documented as load-bearing:

- **`super_critical`** — deleted because *the sum rule forbids that outcome for any field that varies*. A verdict that physics makes impossible should not be in the enum.
- **A fixed `collapse_error ≤ 0.05` gate** — deleted because across every run it *"never once exceeded 0.035 — it passed unconditionally and decided nothing, leaving 'critical' resting on the slope alone."* A gate that always passes is not a gate.

The test file preserves the deletion rationale in a comment on the `VERDICTS` set, so nobody re-adds them by accident. There is even a **negative test** asserting a removed field cannot silently return.

### It knows its own noise floor

The single best idea in the measurement layer: the scale-free scan computes the curve-collapse error **across sizes**, and then computes the same error **across seeds at fixed size**. The ratio is the verdict.

A collapse only counts if the across-size spread is no worse than ~1.5× the across-seed spread. In other words: *the instrument measures its own noise and refuses to report a signal smaller than it.*

Related candor: the stated seed-to-seed slope movement is ±0.09 against a threshold band of 0.08→0.25 — *"half the width of the entire band."* The code says out loud that a single run is, by construction, uninformative here.

### It gates the artefact at the boundary, not the view

The lift tables (condition → pattern association) have a classic pathology, and the comment diagnoses it exactly:

> A motif seen once, under a condition also seen once, gives P(M|C)=1 and P(M)=1/n, so lift = n exactly. On Alpha at 1500 ticks that produces lift 30.0 from 30 instances and 16.0 from 16 — **the sample size wearing a discovery's clothes.**

The support gate lives in the API, not the page, *"so no consumer can print singleton lift by accident."* The response also exposes `singletonRows` and `topLiftEqualsInstances` so the page shows its own reasoning.

### It renders absence as absence

The `/science` page *"leaves a slot visibly blank — not greyed — where the evidence cannot carry a number."* `null` renders as a blank rather than a verdict.

The anti-hype rule from the earliest tech-debt list — *Forecast Lite must not be marketed as real AI* — began as a copywriting constraint and matured into an enforced architectural invariant. That is a rare direction of travel.

### Determinism, verified

`determinism_signature` builds a canonical payload — universe scalars, event type counts, all regions and species sorted by id, all live populations sorted by key — serializes with `sort_keys=True`, and SHA-256s it. Same seed, same 64-hex digest. Tested at four levels, including a 300-tick chirality run and whole-dict equality on the scale-free scan.

One caveat the project does not state: the signature is *structural*, not golden. It proves same-seed self-consistency inside one process; it is not checked against a committed constant, so an unintended behavioural change to the engine breaks no test by breaking a hash.

**123 tests across 7 files.** The test names are declarative claims rather than descriptions:

- `test_without_the_field_the_universe_locks_into_domains_and_is_denied_life`
- `test_racemization_can_grant_life_while_nothing_ever_latches`  *(the hollow phase)*
- `test_one_seed_reports_no_spread_and_cannot_be_called_critical`
- `test_verdict_stays_inconclusive_when_the_interval_straddles_a_threshold`
- `test_critical_needs_both_a_clear_slope_and_a_collapse`
- `test_the_chronicle_is_its_own_world_not_a_metronome`
- `test_a_reported_decline_is_one_the_population_actually_took`
- `test_intelligence_era_is_unreachable_in_t1`

Read that list again. Those are hypotheses, pinned.

---

## 6. The honest negatives

A project's credibility is best measured by what it says when the answer is no. Evoverse has an unusual number of these, and they are load-bearing.

**"An honest negative: β_c does not scale."** A companion hypothesis — that the critical field strength should scale with world size — was stated, tested, and refuted, with the scatter attributed to grid resolution and seed noise. It stayed in the doc.

**Heterochiral selection is inert.** The mismatch penalty — a whole subsystem — is a transient, not a standing pressure. The design doc records 17 mismatched populations at tick 60, 4 at tick 100, and 0 from tick 140 onward, permanently, and concedes the subsystem does nothing for ~9,900 of 10,000 ticks. *(I could not reproduce these particular figures: no sweep or benchmark emits mismatch-count-over-time, so this is the one honest negative in the list that is itself unverifiable. The transient's existence is pinned by a test; its shape is not. That is a gap, and it belongs in §7 as much as here.)*

**The Intelligence Era is unreachable by construction.** Because no lineage locks a mind until the cognitive tier ships, the fourth Era is *genuinely unreachable*. Not a bug — a declared vacancy. The Organism Lens has a `mind` mode written into its type system that no code path can currently produce, because the switch was written for it now rather than reshaped later.

**The world cannot yet answer whether it is critical.** See §4.

**The chronicle used to lie, and the lies were deleted.** Earlier versions emitted scripted events on fixed clocks — a resource shift every 13 ticks, a species decline every 17, a collapse every 151 — which *together* were **91% of the chronicle**. Of the decline, the engine's own comment is unsparing: it *"announced a 14% decline and never touched the population, so the chronicle was simply wrong 588 times per run."* Two of the three were removed. One scripted beat remains, and it is labelled as one.

That last item is the ethic in miniature. An event log that reports things that did not happen is not a chronicle; it is a metronome with a vocabulary.

---

## 7. What I found that is still wrong

I would not publish this essay without the audit that accompanied it. In the spirit of the above, here is what a fresh pass turned up. None of it is fatal; all of it is fixable; the fact that it exists is itself the finding.

### The documentation drifts from the code at every seam that isn't executable

- **The glossary defined the refuted metric** — `mean |ee|`, the exact quantity the chirality doc was rewritten to reject and the one that handed life to a chiral glass. *This one was fixed while I was writing this essay*, in a commit that also caught `PERFORMANCE_LOOP.md` sizing disk from a chronicle that was 91% scripted and is now 98% organic. I am leaving the item in, because the interesting part is not that it was wrong; it is that it sat wrong through an entire release while the doc that refuted it sat two files away.
- **A fully-implemented document is headed "not yet implemented."** `CORRELATION_AND_PATTERNS.md` opens with *"Status: design proposal (not yet implemented)"* above 1,009 lines of shipped `diagnostics.py` and 19 tests. The doc contradicts its own body, which cites its own commits.
- **A superseded figure survives in a code comment.** `rules.py` states the field sweep gives "6/10 at 0.002." That figure came from an arbitrary seed list; under the repo's consecutive ensemble it is 8/8 — which my fresh run confirms exactly. The doc was corrected; the comment was not.
- **The documented reproduce command does not run.** `make sweep --param racemization_rate` is given twice in the chirality doc. It fails with `make: unrecognized option '--param'` — the Makefile target passes no arguments through.
- **Ten of the sixteen line anchors in the formulas doc are stale** — `_advance_populations` is cited at 304 and lives at 366. Line numbers are a citation format with a half-life.
- **The published `sub_critical` verdict is not what the scan returns.** At the worker's own default configuration it says `underpowered` (§4). This one is different in kind: it is a claim about an *executable* thing that went stale anyway, because being runnable was never the same as being run. It is also the most consequential, because it is the project's headline scientific self-assessment.

The pattern is nearly singular: **what is not executable has rotted; what is executable is correct.** The formulas themselves are accurate — an audit found no case where a stated formula misdescribes the arithmetic the code performs. The chirality sweeps reproduce almost exactly, including a lock-tick progression (58 → 64 → 69 → 81 → never) that matches the figure recorded when the sweep was written, to within a tick.

The `sub_critical` drift is the instructive exception, and it sharpens the rule. Being *runnable* was not enough; nothing *ran it and compared*. A number that can be regenerated but never is decays at exactly the same rate as one that cannot.

The project already discovered the first half of this and built the cure. The commit that introduced `sweep.py` says it best:

> The docs asserted measurements and the repo could not make them… **It caught a wrong number on its first run, which is the point of it.**

The conclusion is not "unify the documentation." It is *"make the rest of it runnable — and then actually run it."*

### The measurement layer has one asymmetry

Rigor on ξ; almost none on τ. The domain-size power-law exponent is reported from a single state with **no confidence interval, no ensemble, and no verdict** — precisely the sin the scale-free scan was rewritten to avoid. Worse, it uses unweighted least squares on a log-log histogram, which is the textbook-biased power-law estimator (Clauset–Shalizi–Newman): no MLE, no `x_min` selection, no goodness-of-fit test. R² on log-log points is not evidence of a power law. Since τ is offered as "the pattern-level signature of the same criticality," this is the layer's largest gap.

**Other gaps, in rough priority:**

1. **No null model.** Nothing compares measured ξ, τ, lift, or convergence against a shuffled baseline. There is no answer to "what would this number be if the structure were destroyed?"
2. **`ticks` is never scaled with L.** The scan advances every world size for the same tick count. If equilibration time grows with L — it generally does — larger worlds are measured further from steady state, biasing the very ξ-vs-L slope the verdict reads.
3. **Only four sizes, spanning L = 12→24.** A factor of two. Scale-free claims conventionally want a decade. This one is nowhere acknowledged.
4. **`sweep.py` has zero test coverage.** The four-phase classifier — the project's headline scientific claim — is entirely unpinned.
5. **Multiple comparisons unhandled.** Four fields, hundreds of lift pairs, no correction, no p-values.
6. **Lift is association only.** The catalyst system is a natural `do`-operator and is never used as one — the one intervention primitive the project owns, unexploited.

### The tick is not quite a pure function

- **Migration writes into the snapshot being iterated.** The loop iterates a defensive copy, so there is no mutation hazard and newly created populations are correctly deferred to the next tick. But migration increments `population_count` on *sibling objects still ahead in that snapshot* — so whether a population grows on its pre- or post-migration count depends on where it sits in dict insertion order. Deterministic, and a function of insertion order rather than of the population set. Two-phase it (compute all moves, then apply) and the tick becomes order-free.
- **`SimulationEngine.__init__`'s `seed` parameter is dead** — written once, never read. All draws use `state.seed`. `SimulationEngine(seed=9999)` silently runs seed 4211.
- **Genesis is not parameterized.** The seeder takes no rules and is almost entirely magic numbers; `seed_bias_max` is exposed and validated through the admin API but unreachable. The claim "all constants are runtime-tunable" is not true.
- **Rules are not part of the state**, so replay reproduces only if the caller reconstructs them.

### The two-tier thesis is half-empty, and the empty half is the ambitious one

`model_coherence`, `prediction_error`, `mind_lock_threshold` — **zero occurrences in the backend.** T2 is five undefined fields and a boolean nothing assigns. The thesis "same math, two tiers" derives its entire persuasive force from the tier that exists.

To the project's credit, it says so. But an essay should not: **"a racemic mind cannot act; a homochiral mind commits to one model and can be wrong" is a definition, not a prediction.** Until it forbids an observation, it is not yet a hypothesis.

### One place where narrative wears a lab coat

The Conway alignment scores — 32/72/56 — are presented in the syntax of measurement. No code produces them; no rubric defines them. They are a considered judgment, which is fine and even admirable. But they are printed beside numbers that *are* measured, without a marker distinguishing the two.

This is worth naming because the project has the antibody already. Its own rule about the Kılıç convergence — **"Convergence is a compass, not a certificate"** — is exactly the guardrail the alignment table needs and doesn't have.

---

## 8. What I would add

Ordered by ratio of credibility gained to work required.

**0. Correct the `sub_critical` claim, and make the verdict regenerate itself.** It is the project's headline scientific statement and it no longer reproduces (§4, §7). Fixing the sentence is ten minutes. The real fix is a CI job — or a `make science` — that re-runs the scan and fails when the published verdict and the measured one disagree. That single job would have caught this, and would catch the next one.

**1. Fix the four contradictions.** Glossary metric, status header, the stale 6/10 comment, the broken `make` target. All verified, all mechanical, all currently emitting false information to anyone reading.

**2. Make the remaining claims runnable.** Continue what `sweep.py` started. Every asserted number gets a command or a test. Delete line anchors — they are guaranteed to rot; reference symbols instead. If a figure cannot be produced by `make`, it should not be in a doc.

**3. Give τ the same rigor as ξ.** MLE with `x_min` selection and a goodness-of-fit test, or demote it explicitly to "suggestive, not evidence." The current asymmetry is the easiest thing for a hostile reader to attack, and they would be right.

**4. Add a null model.** Shuffle the region field, recompute ξ. Shuffle lineages, recompute the convergence index. One afternoon's work, and it converts every existing number from "a number" into "a number that beats chance." This is the single highest-leverage addition available.

**5. Use the catalyst as a `do`-operator.** The project owns an intervention primitive and treats it as a product feature. Pulse a region, measure the counterfactual against an un-pulsed replay of the same seed — determinism makes the counterfactual *exact*, which is a luxury no field scientist has. This turns the lift tables from association into causation and is, I think, the most scientifically interesting unexploited asset in the codebase.

**6. Treat `underpowered` as a finding about the engine, not the scan.** ξ sits at 1–2 cells at every world size (§4), so the correlations are local and the ruler is one cell wide. Widening the size ladder cannot resolve a length shorter than the lattice; only longer-range coupling in the engine can. The scan is working — it is the world that is short-sighted. *(Scaling `ticks` with L and widening the ladder are still worth doing, because both currently bias the slope, but neither is the fix.)*

**7. Pin `sweep.py`.** The phase classifier deserves the same test discipline as everything downstream of it.

**8. Decide what a tick is.** *How many years is one tick?* has been open question #3 since the PRD and is still open at 0.4.0 — the Era bands and the digest cadence run on placeholder world-age constants. The product's central user-facing unit rests on an undecided constant. Every "Alpha Age" shown to a user is a number with no denominator.

**9. Either build T2 or reframe it.** State it as something that could be false. "A lineage whose model coherence locks will make systematically *worse* predictions in novel regions than an uncommitted one, before it makes better ones" is a hypothesis. The current phrasing is a definition wearing one.

**10. Mark the levels.** Three kinds of claim live in these docs without a distinguishing mark: dynamical-system claims (measured, falsifiable), product bets (unfalsifiable, legitimate), and design-lineage judgments (considered, not measured). A one-line badge on each would cost nothing and would stop the strongest work from lending unearned authority to the weakest.

**11. The essay-shaped gap: individuals.** The aggregate model is a Phase-1 decision that has become a philosophical ceiling. Homochirality is a claim about *molecules*; the world models *populations*. The Micro Life Field and the Organism Lens are honest projections of aggregate state — deliberately not canonical — but that means the thesis's subject matter and the simulation's subject matter never actually meet. This is the deepest open question in the project and it deserves to be stated in the essay rather than discovered by a reader.

---

## 9. What it adds up to

Evoverse is three things stacked, and they are worth separating because they have very different strengths.

**As a product**, it is a persistent observatory with a real retention thesis — the chronicle as the reason to return, the catalyst as influence without control. That thesis is untested; the metrics exist and no cohort has run against them.

**As a simulation**, it is a deterministic, event-sourced, aggregate ecology with a genuinely interesting chirality subsystem. The phase diagram in §3 is a real result: four phases, a critical slowing-down signature nobody looked for, and a demonstration that autocatalysis alone yields a chiral glass rather than a living world. It is a statement about a class of models, not about Earth, and it does not pretend otherwise.

**As an epistemic artifact**, it is the most interesting of the three, and the least expected. Somewhere between a product manager's worry about boredom and a starling-flock correlation length, this project acquired a conscience. It built instruments that refuse to answer. It deleted a verdict because physics forbade it. It deleted a gate because the gate always passed. It renders a blank where a number would be a lie.

And then — the detail I did not expect to find — its own instrument turned out to be more honest than its own press release. The project published `sub_critical` about itself. Run it today and it says `underpowered`: *I cannot resolve this.* The apparatus is stricter than the sentence written about it, which is the right direction for that error to point, and the reason I trust the apparatus.

The founding question was *"why should the user come back?"* The answer it arrived at, by a route nobody planned, is: **because the world is really running, and the project can prove it — including proving the parts that don't work yet.**

The gap between that and a scientific instrument is smaller than it looks. It is roughly: a null model, an honest τ, a counterfactual built from the catalyst, and one discipline this project half-invented and should finish — **never write down a number the repository cannot regenerate, and then regenerate it on every commit.** The first half is why the chirality results still hold. The second half is why the criticality claim didn't.

---

## Appendix: reproducing this essay

Every table above came from these commands, run at v0.4.0 on a 108-region world, 8-seed consecutive ensembles from base seed 4211:

```bash
# Field-strength sweep (§3, first table)
PYTHONPATH=backend python -m app.simulation.sweep --param field_strength

# Racemization sweep (§3, second table)
PYTHONPATH=backend python -m app.simulation.sweep --param racemization_rate

# Phase diagram (§3)
PYTHONPATH=backend python -m app.simulation.sweep --phase

# Scale-free scan (§4) — the worker's own default configuration
PYTHONPATH=backend python -m app.simulation.benchmark --ticks 2000 --scale-free --scan-seeds 8

# The whole test suite (§5) — 123 tests
PYTHONPATH=backend pytest backend/tests
```

Benchmark context for the scan above: 2,000 ticks in ~3.4 s (595 ticks/sec), 893 events, 19 species, 2 collapsed regions, determinism signature `b85e71e9…`.

The scan reports `underpowered` at this configuration, not the `sub_critical` recorded in `CHANGELOG.md`. If you reproduce only one thing from this essay, reproduce that one.

Note that `make sweep --param …`, as documented in `CHIRALITY_AND_MIND.md`, does **not** work — the Makefile passes no arguments through. Use the module invocation above. That this essay's own reproduce section has to carry a correction is, fittingly, the point of §7.

---

### References

- Frank, F. C. (1953). On spontaneous asymmetric synthesis. *Biochimica et Biophysica Acta*.
- Cavagna, A., Cimarelli, A., Giardina, I., Parisi, G., Santagati, R., Stefanini, F., Viale, M. (2010). Scale-free correlations in starling flocks. *PNAS*.
- Clauset, A., Shalizi, C. R., Newman, M. E. J. (2009). Power-law distributions in empirical data. *SIAM Review*.
- Chan, B. W.-C. (2019). Lenia: Biology of Artificial Life. *Complex Systems*. arXiv:1812.05433
- Conway's Game of Life — LifeWiki. https://conwaylife.com/
- Ozturk, S. F., Sasselov, D. D. (2022). On the origins of life's homochirality. *PNAS*.

*Source: [github.com/…/evoverse](https://evoverse.studiobinary.co) · MIT · Design notes in `docs/`*
