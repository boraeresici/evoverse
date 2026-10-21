# Evoverse — Novelty & Surprise (Prediction-Error Reading)

> **Status:** design proposal (not yet implemented). This document specifies a
> deterministic **diagnostic** for `benchmark.py`: a two-tier (short-/long-term)
> model of what is *typical* in the world, and a **surprise** reading — `−log p` of
> the present against that model. It is a measurement layer, not a new simulation
> rule — it observes the engine and its event log, it does not change either. It is
> the temporal companion to [`CORRELATION_AND_PATTERNS.md`](CORRELATION_AND_PATTERNS.md):
> Part A measures *criticality* (ξ ∝ L), Part B counts *recurrence*, Part C reads
> *condition → pattern* association; this adds Part D — **history → surprise**.

Like its siblings, this uses information theory as **orientation, not endorsement**.
A surprise spike marks an event that is improbable *given the model's own past* — it
does **not** prove the event is biologically meaningful. Surprise is a compass, not a
certificate (see [CHIRALITY_AND_MIND §9](CHIRALITY_AND_MIND.md)).

---

## 1. Motivation

The census in [`CORRELATION_AND_PATTERNS.md`](CORRELATION_AND_PATTERNS.md) answers
*what recurs* and *how diverse the world is now* (`entropy`, `effectiveCount` in
[`diagnostics.py`](../backend/app/simulation/diagnostics.py) `_diversity`). It cannot
answer a different, load-bearing question:

> **How *unexpected* is the present, given everything the world has done before?**

Diversity and surprise are different measurements. A world can be highly diverse and
completely unsurprising (the same rich mix, tick after tick), or briefly un-diverse
and enormously surprising (a single motif no lineage has ever produced). Shannon says
it plainly: information = `−log p`. A high-frequency motif is high-`p`, low-surprise;
a first-ever motif is low-`p`, high-surprise. **The rare event is the informative one**
— which is exactly the signal a recurrence count buries and a *"keep what repeats"*
filter would throw away.

So the deliverable is a diagnostic that builds a model of the typical and reads the
present against it:

> **D.** `novelty_trace(state)` → per-observation surprise `−log p̂(x | LTM)`, a
> ranked list of the most surprising recent motifs/events (with support), and a
> **novelty budget** (total surprise per window) — how much genuinely new structure
> the world is producing right now.

Read-only, deterministic, replayable — same `(seed, ticks)` ⇒ same surprise trace,
so results are comparable across runs and commits, exactly like Parts A–C.

### 1.1 Why this is the missing half

Part C already computes a *static* surprise: `lift(m, c) = P(m | c) / P(m)` — is a
motif over-represented *given a co-located condition* ([`diagnostics.py`](../backend/app/simulation/diagnostics.py)
`_lift_table`). This part is the **temporal generalisation** of that same
information-theoretic form: `P(motif_now | model-of-the-past)`. Same shape, different
conditioning axis — history instead of co-location. The two compose: an observation
can be scored as unexpected *in this condition* **and** *at this point in the world's
history*.

---

## 2. The theory we are reading (predictive processing, precisely)

One equation carries the whole design. For an observation `x` drawn against a model
`M` of the typical:

```
surprise(x) = −log₂ p̂(x | M)                    # Shannon self-information / "surprisal"
```

- `p̂(x | M)` high (x is typical) ⇒ surprise ≈ 0.
- `p̂(x | M)` low (x is rare) ⇒ surprise large.
- `x` **never seen** in `M` ⇒ surprise at its ceiling, *finite* only because the model
  is smoothed (§4.3). This is the load-bearing case: pure novelty must score
  **maximally**, not be dropped.

This is the predictive-processing / free-energy reading: *information is created not
in the memory but in the reading against it.* The memory is the model of the expected;
the surprise is the prediction error. The two-tier structure below is only there to
make "the expected" a **moving** target that tracks the world's current regime rather
than averaging its whole history flat.

### 2.1 What this is NOT

| | Looks like | Actually is |
|---|---|---|
| A `keep-if-refreshed / drop-if-not` cache (LFU/TTL) | a low-pass filter — keeps the frequent, drops the rare | **the opposite** — the rare is the *output*; nothing is discarded, decay only re-weights what counts as typical |
| The census `entropy` | a diversity number | **surprise is against the past**, not a snapshot of now |
| A new engine rule | feedback into `F` | **read-only**; the moment surprise feeds back into the grid it becomes T2 (§7) |

---

## 3. Part D — the two-tier model of the typical

The consolidation architecture the design started from (a fast episodic tier that,
through repetition, writes a slow durable tier) maps to **two decaying counters** over
the exact motifs Part B already canonicalises. No grid, no cache eviction — two
weighted histograms.

### 3.1 STM and LTM as decayed `Counter`s

```
STM  = Counter over the last W ticks           # short-term, high-resolution — "now"
LTM  = exponentially-decayed accumulator        # long-term — "the model of typical"
```

Per step of width `ΔW`, before folding STM in, LTM ages by its half-life `H` (H ≫ W):

```
decay      = 2 ** (−ΔW / H)
LTM[k]    *= decay          for all k          # forgetting, not deletion
LTM[k]    += STM[k]         for all k          # consolidation — repetition writes the slow tier
```

`H` is the only thing that makes "typical" mean *recently typical*: a motif common
10,000 ticks ago and gone since decays out of the model, so a return of it can read as
surprising again. **Nothing is ever removed as unworthy** — a count decays toward zero
but the key stays scoreable; `α`-smoothing (§4.3) is what actually bounds the surprise
of the never-seen.

### 3.2 The observation stream — what feeds STM

Two feed modes, both read-only, both already backed by existing state:

- **Event-stream mode (cheapest — no replay).** `state.events` is append-only and
  tick-ordered, each event carrying `(tick, id, event_type, species_id, region_id,
  payload)`. Reuse the per-species event sequences that `_event_ngram_census` already
  builds ([`diagnostics.py`](../backend/app/simulation/diagnostics.py)); treat each
  n-gram as an observation and score `−log p̂(ngram | LTM)`. This runs against **live
  Alpha** the same way the Science page's `getDiagnostics()` does — the event log *is*
  the history.

- **Trace mode (full census, deterministic replay).** Reuse the `--trace K` machinery
  of [CORRELATION_AND_PATTERNS §5.2](CORRELATION_AND_PATTERNS.md): re-advance sampling
  every `K` ticks, **diff** `pattern_census`, and stamp each *newly appeared* motif as
  the STM observation for that window. This scores morphotype / spatial / domain /
  lineage motifs too, not just event types. Replay stays deterministic, so a traced
  novelty run is as reproducible as a static one — **and the engine is never touched**
  (history is re-derived by replay, not stored per tick).

### 3.3 Consolidation as a measurable curve

Because promotion is `≥ k` recurring windows folding into LTM, "learning" is directly
observable: a motif's surprise **decays as it consolidates**. A newly emerged motif
spikes, then — if it recurs — its `p̂` climbs and its surprise falls toward zero (it
became typical); if it never recurs, it stays a one-off, flagged and logged, never
promoted. The trace can emit `ticks_to_consolidate(motif)` (windows from first
appearance until surprise crosses a low band) as a first-class output — the codebook
being learned, in numbers.

---

## 4. The surprise reading

### 4.1 Per-observation surprise

For every observation `x` in the current STM window:

```
        LTM[x] + α
p̂(x) = ─────────────────          # add-α (Laplace / Good-Turing-flavoured) smoothing
        Σ LTM + α·|V|

surprise(x) = −log₂ p̂(x)
```

`|V|` is the count of distinct keys ever seen (the model's vocabulary). `α` sets the
surprise ceiling of a never-seen `x`: with `α` small, an unseen motif scores near
`log₂(Σ LTM / α)` — large but finite. **This single term is why novelty is flagged
rather than dropped**: the first-ever motif is maximally surprising by construction.

### 4.2 Window aggregates — the novelty budget

Per window, aggregate the per-observation surprises into two headline numbers:

- **`novelty_budget`** = `Σ_x support(x) · surprise(x)` over newly-appeared `x` — total
  new information the world produced this window. This is the third axis the Science
  page lacks: Part A gives criticality (ξ), Part B gives diversity (entropy), Part D
  gives **unexpectedness**.
- **`peak_surprise`** = `max_x surprise(x)` with its motif and support — the single most
  novel thing that happened.

Always report `support = count(x)` alongside surprise, so a rare-but-high-surprise
coincidence is visibly weak — the same honesty discipline as Part C's `_lift_table`.
A first-ever motif has `support = 1` by definition, so support is not a filter here;
it is context that keeps a one-off from reading as a trend.

### 4.3 Two conditioning axes (optional, composes with Part C)

The base reading conditions only on time: `p̂(x | LTM)`. It can also condition on the
Part C `condition_vector(state, region)` — `p̂(x | LTM, c)` — to ask "unexpected *in
this condition* **and** at this point in history." This is a straight join of the two
diagnostics and needs no new capture; it reuses `condition_vector` verbatim.

---

## 5. Verdicts

Surprise is a continuous signal, so the "verdict" is a small set of bands plus one
guard, all read off the trace — never a point spike alone:

| Observation | Reading |
|-------------|---------|
| sustained low `novelty_budget`, flat | **stationary** — the world is in a settled regime (expected for locked Alpha post-~tick 250) |
| isolated `peak_surprise` spike, no budget rise | **one-off** — a single novel motif, not a regime change |
| `novelty_budget` steps up and stays up | **regime shift** — the model of typical is being rewritten; worth a Chronicle-level reading |
| high budget that **decays** over the next windows | **consolidation** — novelty that the world then learns (surprise → 0) |
| `|V|` still climbing every window | **underpowered / cold model** — LTM has not seen enough history to call anything typical yet; do not report surprise as meaningful |

The cold-model guard matters most: like the ξ ensemble's `underpowered` verdict, a
model that has not warmed up produces surprise everywhere and means nothing. Report
`Σ LTM` and `|V|` so a reader can see whether the model is warm.

---

## 6. API & wiring

Pure functions beside the existing diagnostics in
[`app/simulation/diagnostics.py`](../backend/app/simulation/diagnostics.py); no engine,
domain, schema, or serializer changes.

```python
def novelty_trace(state, *, families=("eventNgrams",), alpha=DEFAULT_ALPHA) -> dict:
    """Event-stream mode: fold state.events into (STM, LTM), return per-window
       surprise, novelty_budget, peak_surprise, and top-surprising motifs with support.
       Runs against live Alpha — no replay."""

def novelty_scan(seed, ticks, *, window, half_life, step, families, alpha) -> dict:
    """Trace mode: deterministic replay, diff pattern_census every `step` ticks, run the
       two-tier model over the census diffs; return the surprise timeline and the
       consolidation curve. Reuses the scale_free_scan / --trace replay convention."""
```

CLI (extends `main()`, off by default so the fast benchmark stays fast):

```
python -m app.simulation.benchmark --novelty              # event-stream surprise, final log
python -m app.simulation.benchmark --novelty-scan --window 25 --half-life 2000 --step 50
python -m app.simulation.benchmark --novelty --json       # machine-readable
```

**Output schema** (new top-level key; existing keys untouched):

```jsonc
{
  "novelty": {
    "mode": "eventStream",              // or "trace"
    "model": { "vocabulary": 214, "ltmMass": 1830.4, "warm": true },
    "window": { "tick": 12000, "budget": 3.71, "peak": { "motif": "SPECIES_EMERGED>DOMINANT>SPECIES_DECLINED", "surprise": 9.2, "support": 1 } },
    "top": [                            // most surprising recent observations (DEFAULT_TOP)
      { "motif": "SPECIES_EMERGED>DOMINANT>SPECIES_DECLINED", "surprise": 9.2, "support": 1, "pHat": 0.0017 }
    ],
    "timeline": [                       // trace mode only
      { "tick": 2000, "budget": 41.3, "vocabulary": 88 },
      { "tick": 2050, "budget": 12.1, "vocabulary": 121 }
    ],
    "verdict": "consolidation"
  }
}
```

### 6.1 Determinism

- No new randomness — a pure fold over `state.events` (event-stream mode) or over the
  deterministic replay diff (trace mode). Same `(seed, ticks)` ⇒ identical output.
- Fold `state.events` in **`(tick, id)` order** and iterate motif keys in sorted order,
  so `Counter` decay and surprise ranking are order-independent (the existing report
  already iterates in sorted id order).
- Half-life decay uses integer tick deltas only — no wall-clock, no `Date.now()`.
- Hash `novelty` into the existing `determinism_signature` guard alongside `patterns`
  and `correlation`.

---

## 7. Non-goals & open questions

- **Non-goal — feeding surprise back into the engine.** This is observation only. The
  moment `novelty` is read by a rule (e.g. spawning a catalyst where surprise is high,
  or injecting a recurring motif back into the grid), it stops being a measurement and
  becomes a term in `F` — a memory-augmented cellular automaton in Alonso-Sanz's sense
  (cell state computed from its own past). That is a legitimate way to make the
  substrate itself generative, but it is **T2 (the cognitive layer)**, a deliberate
  design decision, and "it emerged on its own" is no longer available as an explanation
  once surprise steers the dynamics. Keeping Part D read-only is exactly what preserves
  the "no engine change" contract.
- **Non-goal — claiming a surprise spike is biologically meaningful.** It marks
  model-relative improbability, full stop (cf. [CHIRALITY_AND_MIND §9](CHIRALITY_AND_MIND.md)
  and Part C's honesty note).
- **Open — the four knobs are product decisions, not calibration.** Expose as function
  args and pick after first runs:

  | knob | sets |
  |------|------|
  | `W` (STM window) | the resolution of "now" — short = reactive, long = smoothed |
  | `H` (LTM half-life) | how far back "typical" looks; how fast it re-learns after a regime shift |
  | `α` (smoothing) | the surprise ceiling of a never-seen observation |
  | `families` | which census levels are scored (event n-grams are free; morphotype / spatial / domain need trace mode) |

- **Open — event-stream vs trace as the primary mode.** Event-stream is free and live
  but only sees event-type sequences; trace sees full spatial/morphotype structure at
  replay cost. Report both first; pick per family after measuring.
- **Open — surprise ceiling vs vocabulary growth.** While `|V|` is still climbing every
  window the model is cold and every observation looks novel. Needs a warm-up gate
  (§5) tuned against how long Alpha takes to populate the vocabulary.
- **Open — relation to the Chronicle.** A sustained `novelty_budget` step is a natural
  candidate for an *organic* Chronicle beat (unlike the `synthetic: true` scripted
  beats). Whether Part D should *feed* the Chronicle is itself a §7 boundary question:
  reading the budget to author a narrative beat is still observation; using it to
  perturb the world is not.

---

## 8. Build order (slices)

1. **`novelty_trace` (event-stream mode)** over `state.events`, reusing the
   `_event_ngram_census` sequences, with `α`-smoothed `−log p̂` and the two-tier
   `Counter`s. `--novelty` CLI, `novelty` block in the report. Golden-value test on the
   default seed.
2. **Window aggregates** — `novelty_budget`, `peak_surprise`, `top` with support; the
   verdict bands and the cold-model guard.
3. **`novelty_scan` (trace mode)** on `pattern_census` diffs via the existing `--trace`
   replay; the surprise **timeline** and the **consolidation curve**
   (`ticks_to_consolidate`).
4. **Condition-joined surprise** — `p̂(x | LTM, condition_vector)`, composing Part C's
   `condition_vector` with the temporal model.
5. Fold `novelty` into the `determinism_signature` guard; a `CriticalityPanel` sibling
   on the Science page plotting the novelty budget beside ξ and entropy.
