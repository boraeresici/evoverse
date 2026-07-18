from __future__ import annotations

from dataclasses import dataclass, field

from app.domain import CatalystActionType


@dataclass(frozen=True)
class CatalystRules:
    daily_limits: dict[CatalystActionType, int] = field(
        default_factory=lambda: {
            CatalystActionType.ENERGY_PULSE: 3,
            CatalystActionType.MUTATION_PULSE: 1,
            CatalystActionType.RESOURCE_BURST: 1,
        }
    )
    effect_ticks: int = 8
    followup_ticks: int = 3
    strength: float = 0.18


@dataclass(frozen=True)
class RegionRules:
    energy_delta_min: float = -0.035
    energy_delta_max: float = 0.04
    resource_delta_min: float = -0.04
    resource_delta_max: float = 0.038
    stability_delta_min: float = -0.018
    stability_delta_max: float = 0.016
    energy_equilibrium: float = 0.56
    resource_equilibrium: float = 0.52
    stability_equilibrium: float = 0.58
    energy_reversion_factor: float = 0.018
    resource_reversion_factor: float = 0.02
    stability_reversion_factor: float = 0.026
    resource_stability_baseline: float = 0.4
    resource_stability_bonus_cap: float = 0.02
    resource_stability_factor: float = 0.018
    # Consumer-resource coupling: what a region's populations draw out of it each
    # tick, as sum(population * energy_consumption) / scale. Without this the
    # regions drifted on their own noise no matter how much life they carried —
    # life was a passenger, `Population.energy_consumption` was computed, stored
    # and served but read by nothing, and nothing could ever deplete.
    #
    # Scale is the divisor that turns a headcount into a resource draw. For
    # reference, regrowth (reversion toward equilibrium) tops out at
    # resource_reversion_factor * resource_equilibrium = 0.0104/tick, and the
    # busiest region on the base seed carries sum(N*c) ~ 2500. The two meet near
    # scale = 250k, so anything far above that is a rounding error and anything
    # far below strips the map bare.
    #
    # `resource_density` is rounded to 3dp every tick, so a draw under 0.0005 —
    # a thin region, at this scale — contributes nothing on any *single* tick and
    # only tells across many. The coupling is therefore blunter for sparse regions
    # than the arithmetic suggests; the busy ones carry it.
    consumption_pressure_scale: float = 400000
    collapsed_stability_penalty: float = 0.006
    collapsed_energy_penalty: float = 0.004
    mutation_stability_penalty_factor: float = 0.08
    # How far a region's resource must move *since the chronicle last reported it*
    # to be worth reporting again. This is a reporting threshold — it does not
    # touch the dynamics, only what gets told.
    #
    # It used to be 0.16 measured against the previous tick, which no region could
    # ever reach: a single tick moves at most ~0.057 (walk +/-0.04, reversion, draw),
    # so the rule fired exactly zero times in 10,000 ticks and the 13-tick scripted
    # shift was the only "resource shift" Alpha ever had. The value was never the
    # problem — 0.16 is the 90th percentile of a 25-tick window, i.e. someone chose
    # it for a trend and wired it to a tick. Measured against the last report the
    # world turns out to be full of real movement: 16,411 shifts of >=0.16 per
    # 10,000 ticks, 21x the scripted rate it was covering for.
    #
    # 0.32 is roughly 0.52 -> 0.20, normal to scarce: unambiguous, not noise. It
    # yields ~2,650 per 10,000 ticks, about 25 per region — a notable resource event
    # every ~400 years of Alpha Age.
    resource_shift_threshold: float = 0.32
    # Resource depletion -> stability. The existing resource_stability term is
    # clamped to +/-0.02 around a 0.4 baseline, so its deepest pull is -0.00036/tick
    # against a reversion to 0.58 — stability answers only to its own noise and the
    # deepest a heavily-drawn region settles is ~0.36, never reaching
    # collapse_stability_threshold (0.16). That is why nothing collapsed on its own
    # and the 151-tick scripted beat was the only collapse Alpha had. This term adds
    # an unclamped penalty once a region is drawn below stability_depletion_threshold,
    # proportional to the shortfall, so a depletion spiral can trip the organic
    # collapse gate. Sized (measured) so busy regions hover near collapse and cross
    # it on a noise dip, not so every region flatlines. See sira.md for the sweep.
    stability_depletion_threshold: float = 0.22
    stability_depletion_factor: float = 0.06
    collapse_stability_threshold: float = 0.16
    collapse_resource_threshold: float = 0.18
    recovery_stability_threshold: float = 0.34
    recovery_resource_threshold: float = 0.32
    recovery_energy_threshold: float = 0.3


@dataclass(frozen=True)
class PopulationRules:
    habitat_fit_divisor: float = 3.0
    growth_baseline: float = 0.31
    growth_factor: float = 0.14
    density_pressure_cap: float = 0.16
    density_pressure_scale: float = 180000
    collapse_penalty: float = 0.09
    migration_baseline: float = 0.42
    migration_trait_factor: float = 0.2
    decline_min_previous_population: int = 500
    # Fraction of `decline_reference_population` a count must fall under to be
    # reported as a decline. Reporting only — the dynamics do not read it.
    #
    # It used to be 0.72 against the *previous tick*: a 28% single-tick crash, when
    # the worst tick this world can produce loses ~11% and the realistic floor is
    # ~1%. It fired zero times in 10,000 ticks. Measured against the lineage's peak
    # instead, 0.60 — down 40% from its high-water mark — is a genuine collapse and
    # fires ~1,095 times per 10,000 ticks.
    decline_population_ratio: float = 0.60
    severe_decline_percent: int = 40
    migration_min_population: int = 1400
    migration_pressure_threshold: float = 0.48
    migration_fraction: float = 0.04
    migration_min_moving_population: int = 20


@dataclass(frozen=True)
class SpeciationRules:
    candidate_min_population: int = 1800
    interval_ticks: int = 149
    child_population_fraction: float = 0.16
    child_min_population: int = 80
    energy_consumption_base: float = 0.1
    energy_consumption_efficiency_factor: float = 0.28
    efficiency_delta_min: float = -0.08
    efficiency_delta_max: float = 0.11
    adaptation_delta_min: float = -0.07
    adaptation_delta_max: float = 0.12
    cooperation_delta_min: float = -0.05
    cooperation_delta_max: float = 0.08
    mobility_delta_min: float = -0.06
    mobility_delta_max: float = 0.1
    resilience_delta_min: float = -0.08
    resilience_delta_max: float = 0.1


# The chronicle once had scripted beats — a 13-tick resource shift, a 17-tick species
# decline, and a 151-tick collapse — that together wrote 91% of it, because the organic
# rules they stood in for had thresholds written for trends and wired to single ticks.
# The shift and decline were fixed by reading thresholds against the last reported value
# (`resource_shift_threshold`); the collapse was retired once stability learned to answer
# to depletion (`stability_depletion_*` in RegionRules). No `ChronicleRules` remain — the
# chronicle is 100% organic. See docs/SIMULATION_FLOW_AND_FORMULAS.md §8.


@dataclass(frozen=True)
class SpeciesStatusRules:
    extinct_population: int = 12
    dominant_share: float = 0.82
    dominant_min_population: int = 4500
    declining_population: int = 650
    emerging_generation_min: int = 1
    emerging_age_window: int = 80


@dataclass(frozen=True)
class ChiralityRules:
    """Molecular symmetry-breaking (T1). See docs/CHIRALITY_AND_MIND.md §5–§6.1.

    Only the T1 bifurcation + avalanche knobs live here; inheritance, selection,
    the Era gate, and the cognitive tier (T2) arrive in later slices.
    """

    seed_bias_max: float = 0.02
    amplify_k: float = 0.06
    noise_scale: float = 0.03
    # Thermal racemization: the back-reaction that pulls any excess toward 50/50.
    # In real chemistry amplification always races this; with no opposing term the
    # cubic gain `amplify_k` had nothing to beat, so every region committed no
    # matter what and the gate could not be missed.
    #
    # The two together give the pitchfork an actual control parameter,
    # mu = amplify_k - racemization_rate, which is what makes this a bifurcation
    # rather than a permanent post-bifurcation regime: mu > 0 leaves ee = 0
    # unstable and a region commits; mu <= 0 makes racemic stable and no number of
    # ticks will produce a hand.
    #
    # But mu > 0 is not enough to *latch*. Ignoring field and noise, the drift
    # settles at ee* = sqrt(1 - racemization_rate / amplify_k), which falls below
    # `ee_lock_threshold` long before mu reaches zero. Past that, regions hover
    # short of the latch forever — and because the life gate reads the universe
    # mean rather than the locks, a universe there still *earns Stabilization while
    # no lineage ever adopts a hand*. Measured: 0.020 leaves 0/108 regions locked
    # with the era still granted. Keep this well under that cliff (~0.018 measured;
    # the naive ee* formula puts it at 0.011, but the latch is an absorbing barrier
    # so noise carries regions over it). At 0.008, ee* = 0.93 and all 108 latch.
    racemization_rate: float = 0.008
    # Universe-wide symmetry-breaking field — the analogue of Ozturk & Sasselov's
    # magnetized surface (CISS). Without it, each region's hand is set by its own
    # local noise and the map freezes into opposing domains: locally locked,
    # globally racemic. A uniform field makes every region fall the same way, so
    # one hand wins everywhere — which is the whole point of the magnetic
    # mechanism, and why life is L-handed *everywhere* rather than in patches.
    # Measured on the 10-seed sweep: 0.0 -> 0/10 single-handed universes,
    # 0.002 -> 6/10, 0.005 -> 10/10. The field's sign is drawn per seed, so which
    # hand a universe gets stays contingent while being global.
    field_strength: float = 0.005
    ee_lock_threshold: float = 0.9
    avalanche_bleed: float = 0.05
    avalanche_min_source: float = 0.75
    # Chiral central dogma: one-way inheritance + heterochiral selection (§6.2–6.3).
    inherit_flip_chance: float = 0.01
    heterochiral_growth_penalty: float = 0.35
    heterochiral_lethal_load: float = 0.85
    heterochiral_lethal_decline: float = 0.5
    # Two-tier Era gate (§6.4): homochirality earns Stabilization (chemistry → life);
    # homochirality *and* a mind-locked lineage earn Intelligence (life → mind).
    life_gate_index: float = 0.8
    mind_gate_index: float = 0.92


@dataclass(frozen=True)
class UniverseRules:
    collapse_ratio_stability_penalty: float = 0.18


@dataclass(frozen=True)
class SimulationRules:
    catalyst: CatalystRules = field(default_factory=CatalystRules)
    region: RegionRules = field(default_factory=RegionRules)
    population: PopulationRules = field(default_factory=PopulationRules)
    speciation: SpeciationRules = field(default_factory=SpeciationRules)
    species_status: SpeciesStatusRules = field(default_factory=SpeciesStatusRules)
    universe: UniverseRules = field(default_factory=UniverseRules)
    chirality: ChiralityRules = field(default_factory=ChiralityRules)


DEFAULT_SIMULATION_RULES = SimulationRules()
