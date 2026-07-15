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
    collapsed_stability_penalty: float = 0.006
    collapsed_energy_penalty: float = 0.004
    mutation_stability_penalty_factor: float = 0.08
    resource_shift_threshold: float = 0.16
    collapse_stability_threshold: float = 0.16
    collapse_resource_threshold: float = 0.18
    recovery_stability_threshold: float = 0.34
    recovery_resource_threshold: float = 0.32
    recovery_energy_threshold: float = 0.3
    forced_collapse_stability: float = 0.12
    forced_collapse_resource: float = 0.13
    forced_resource_rise_delta: float = 0.18
    forced_resource_fall_delta: float = -0.19


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
    decline_population_ratio: float = 0.72
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


@dataclass(frozen=True)
class ChronicleRules:
    forced_resource_shift_interval: int = 13
    forced_resource_rise_interval: int = 26
    forced_decline_interval: int = 17
    forced_decline_percent: int = 14
    forced_collapse_interval: int = 151


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
    chronicle: ChronicleRules = field(default_factory=ChronicleRules)
    species_status: SpeciesStatusRules = field(default_factory=SpeciesStatusRules)
    universe: UniverseRules = field(default_factory=UniverseRules)
    chirality: ChiralityRules = field(default_factory=ChiralityRules)


DEFAULT_SIMULATION_RULES = SimulationRules()
