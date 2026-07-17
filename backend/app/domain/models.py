from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from app.domain.event_payloads import version_event_payload


class Era(StrEnum):
    GENESIS = "Genesis Era"
    EXPANSION = "Expansion Era"
    STABILIZATION = "Stabilization Era"
    INTELLIGENCE = "Intelligence Era"


class BiomeType(StrEnum):
    BASIN = "basin"
    RIDGE = "ridge"
    SPORE_FIELD = "spore_field"
    CRYSTAL_STEPPE = "crystal_steppe"
    ASH_WETLAND = "ash_wetland"
    NORTH_BELT = "north_belt"


class SpeciesStatus(StrEnum):
    EMERGING = "emerging"
    STABLE = "stable"
    DOMINANT = "dominant"
    DECLINING = "declining"
    EXTINCT = "extinct"


class EventType(StrEnum):
    SPECIES_EMERGED = "species_emerged"
    SPECIES_DECLINED = "species_declined"
    MUTATION_DETECTED = "mutation_detected"
    REGION_RESOURCE_SHIFT = "region_resource_shift"
    REGION_COLLAPSE = "region_collapse"
    CATALYST_ACTION = "catalyst_action"
    SYMMETRY_BREAK = "symmetry_break"
    ERA_ADVANCED = "era_advanced"


class CatalystActionType(StrEnum):
    ENERGY_PULSE = "energy_pulse"
    MUTATION_PULSE = "mutation_pulse"
    RESOURCE_BURST = "resource_burst"


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def clamp_signed(value: float) -> float:
    """Clamp to the bipolar chirality range [-1, +1]."""
    return max(-1.0, min(1.0, value))


@dataclass(slots=True)
class Universe:
    id: str
    name: str
    age_years: int
    current_era: Era
    tick: int
    stability_index: float
    # Chirality field (T1). ``chirality_ee`` is the global net handedness in
    # [-1, +1] (0 = racemic).
    #
    # ``homochirality_index`` = |mean ee| over non-collapsed regions, in [0, 1].
    # This is the maturity metric the product and the Era gate read: it is 1 only
    # when *every* region shares one hand. It is deliberately NOT mean |ee| —
    # that measures local order and reads 1.0 for a universe split into equal and
    # opposite domains, i.e. a globally racemic world. Life's homochirality is a
    # global property (all of it runs on one hand), so the gate must measure the
    # global one.
    #
    # ``local_order_index`` = mean |ee| — how far regions are from racemic
    # *locally*, ignoring whether they agree. Kept as a diagnostic: the gap
    # between it and ``homochirality_index`` is exactly the domain problem.
    # ``domain_count`` = connected same-hand regions; 1 means a single hand won.
    #
    # Once ``chirality_locked`` latches, every viable region has broken symmetry
    # irreversibly — but note that says nothing about them agreeing.
    # See docs/CHIRALITY_AND_MIND.md.
    chirality_ee: float = 0.0
    homochirality_index: float = 0.0
    local_order_index: float = 0.0
    domain_count: int = 0
    chirality_locked: bool = False


@dataclass(slots=True)
class Region:
    id: str
    universe_id: str
    x: int
    y: int
    biome_type: BiomeType
    energy_level: float
    resource_density: float
    stability: float
    dominant_species_id: str | None = None
    collapsed: bool = False
    # The resource level the chronicle last told anyone about. A resource shift is
    # a move away from *this*, not from last tick: the world drifts ~0.02/tick and
    # a real shift takes ~50 ticks to build, so a per-tick comparison could never
    # see one. Reporting resets it, which is what keeps a slow slide from becoming
    # a flood of events. See docs/SIMULATION_FLOW_AND_FORMULAS.md §3.
    last_reported_resource_density: float = 0.0
    # Local handedness (T1): drifts through a bifurcation, then avalanches to
    # neighbours and latches. See docs/CHIRALITY_AND_MIND.md.
    chirality_ee: float = 0.0
    chirality_locked: bool = False


@dataclass(slots=True)
class Traits:
    efficiency: float
    adaptation: float
    cooperation: float
    mobility: float
    resilience: float

    def mutated(self, deltas: dict[str, float]) -> Traits:
        data = self.to_public()
        for key, delta in deltas.items():
            data[key] = clamp(data[key] + delta)
        return Traits(**data)

    def distance_to(self, other: Traits) -> float:
        return sum(
            abs(self.to_public()[key] - other.to_public()[key])
            for key in self.to_public()
        )

    def to_public(self) -> dict[str, float]:
        return {
            "efficiency": round(self.efficiency, 3),
            "adaptation": round(self.adaptation, 3),
            "cooperation": round(self.cooperation, 3),
            "mobility": round(self.mobility, 3),
            "resilience": round(self.resilience, 3),
        }


@dataclass(slots=True)
class Species:
    id: str
    universe_id: str
    name: str
    origin_region_id: str
    emerged_at_world_age: int
    status: SpeciesStatus
    generation: int
    parent_species_id: str | None
    traits: Traits
    # Chiral central dogma (T1). ``chirality`` is the lineage's handedness
    # (-1 / 0 / +1; 0 = not yet committed), inherited one-way from the parent and
    # first adopted from the origin region's locked hand. ``heterochiral_load`` is
    # the 0..1 mismatch burden used for selection. See docs/CHIRALITY_AND_MIND.md §6.2–6.3.
    chirality: int = 0
    heterochiral_load: float = 0.0
    # Cognitive homochirality (T2, not yet driven). The Intelligence-Era gate reads
    # this, so it stays unreachable until the cognitive tier sets it. See §6.4–6.5.
    mind_locked: bool = False


@dataclass(slots=True)
class Population:
    species_id: str
    region_id: str
    population_count: int
    energy_consumption: float
    growth_rate: float
    migration_pressure: float
    last_updated_tick: int
    # The level a decline is measured down from: a high-water mark that rises with
    # the population and resets whenever a decline is reported. Growth here is
    # ~+0.6%/tick and the worst single tick loses ~11%, so "lost a fifth since last
    # tick" describes nothing this world can do; "lost a fifth since its peak" is a
    # story it tells constantly. Same threshold, honest resolution.
    decline_reference_population: int = 0


@dataclass(slots=True)
class Event:
    id: str
    universe_id: str
    event_type: EventType
    severity: int
    world_age: int
    tick: int
    title: str
    summary: str
    region_id: str | None = None
    species_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""

    def __post_init__(self) -> None:
        self.payload = version_event_payload(self.event_type, self.payload)


@dataclass(slots=True)
class CatalystAction:
    id: str
    universe_id: str
    region_id: str
    action_type: CatalystActionType
    created_at_tick: int
    expires_at_tick: int
    strength: float
    user_id: str = "local-catalyst"


@dataclass(slots=True)
class AlphaState:
    universe: Universe
    regions: dict[str, Region]
    species: dict[str, Species]
    populations: dict[tuple[str, str], Population]
    events: list[Event]
    catalyst_actions: list[CatalystAction]
    seed: int
    next_event_index: int = 0
    next_species_index: int = 0
    next_action_index: int = 0

    def add_event(
        self,
        event_type: EventType,
        title: str,
        summary: str,
        *,
        severity: int,
        region_id: str | None = None,
        species_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> Event:
        self.next_event_index += 1
        event = Event(
            id=f"evt-{self.next_event_index:06d}",
            universe_id=self.universe.id,
            event_type=event_type,
            severity=max(1, min(5, severity)),
            world_age=self.universe.age_years,
            tick=self.universe.tick,
            title=title,
            summary=summary,
            region_id=region_id,
            species_id=species_id,
            payload=payload or {},
            created_at=f"alpha-age-{self.universe.age_years}",
        )
        self.events.append(event)
        return event

    def next_species_id(self) -> str:
        self.next_species_index += 1
        return f"sp-{self.next_species_index:04d}"

    def next_action_id(self) -> str:
        self.next_action_index += 1
        return f"cat-{self.next_action_index:06d}"
