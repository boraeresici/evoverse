from __future__ import annotations

import math

from app.domain import (
    AlphaState,
    BiomeType,
    Era,
    EventType,
    Population,
    Region,
    Species,
    SpeciesStatus,
    Traits,
    Universe,
)
from app.simulation import event_templates
from app.simulation.randomness import stable_rng
from app.simulation.rules import DEFAULT_SIMULATION_RULES


SPECIES_NAMES = [
    "THERA",
    "VORU",
    "AURAL",
    "NEMI",
    "SOLEN",
    "KARST",
    "IREL",
    "MYON",
    "TEPH",
    "OLOS",
]


def seed_alpha(seed: int = 4211, width: int = 12, height: int = 9) -> AlphaState:
    universe = Universe(
        id="alpha",
        name="Alpha",
        age_years=4211,
        current_era=Era.EXPANSION,
        tick=0,
        stability_index=0.68,
    )
    regions = _seed_regions(seed, universe.id, width, height)
    state = AlphaState(
        universe=universe,
        regions=regions,
        species={},
        populations={},
        events=[],
        catalyst_actions=[],
        seed=seed,
    )
    _seed_species_and_populations(state)
    _recalculate_dominant_species(state)
    _seed_bootstrap_events(state)
    _recalculate_universe_chirality(state)
    return state


def _recalculate_universe_chirality(state: AlphaState) -> None:
    """Aggregate region handedness into the universe-level maturity metrics.

    ``chirality_ee`` is the mean signed handedness; ``homochirality_index`` is the
    mean |ee| over non-collapsed regions (0 = racemic, 1 = fully homochiral).
    Kept identical in seeder and engine so genesis and ticks agree.
    """
    regions = [region for region in state.regions.values() if not region.collapsed]
    if not regions:
        state.universe.chirality_ee = 0.0
        state.universe.homochirality_index = 0.0
        return
    state.universe.chirality_ee = round(
        sum(region.chirality_ee for region in regions) / len(regions), 4
    )
    state.universe.homochirality_index = round(
        sum(abs(region.chirality_ee) for region in regions) / len(regions), 4
    )
    state.universe.chirality_locked = all(region.chirality_locked for region in regions)


def _seed_regions(seed: int, universe_id: str, width: int, height: int) -> dict[str, Region]:
    biomes = list(BiomeType)
    regions: dict[str, Region] = {}
    for y in range(height):
        for x in range(width):
            index = y * width + x + 1
            rng = stable_rng(seed, "region", index)
            biome = biomes[(x * 3 + y * 5 + index) % len(biomes)]
            energy = 0.28 + rng.random() * 0.58
            resources = 0.24 + rng.random() * 0.62
            stability = 0.32 + rng.random() * 0.58
            if index in {18, 73}:
                resources = 0.12 + rng.random() * 0.08
                stability = 0.13 + rng.random() * 0.08
            # Genesis chirality: a tiny deterministic bias off racemic (ee=0), on
            # its own rng stream so it does not perturb the draws above. The
            # bifurcation rule amplifies this into a locked hand. See
            # docs/CHIRALITY_AND_MIND.md §6.1.
            seed_bias_max = DEFAULT_SIMULATION_RULES.chirality.seed_bias_max
            chirality_rng = stable_rng(seed, "chirality", index)
            chirality_ee = (chirality_rng.random() * 2 - 1) * seed_bias_max
            regions[f"region-{index:03d}"] = Region(
                id=f"region-{index:03d}",
                universe_id=universe_id,
                x=x,
                y=y,
                biome_type=biome,
                energy_level=round(energy, 3),
                resource_density=round(resources, 3),
                stability=round(stability, 3),
                chirality_ee=round(chirality_ee, 4),
            )
    return regions


def _seed_species_and_populations(state: AlphaState) -> None:
    origins = [
        "region-006",
        "region-019",
        "region-041",
        "region-064",
        "region-087",
        "region-101",
    ]
    for index, origin_id in enumerate(origins):
        rng = stable_rng(state.seed, "species", index)
        species = Species(
            id=state.next_species_id(),
            universe_id=state.universe.id,
            name=SPECIES_NAMES[index],
            origin_region_id=origin_id,
            emerged_at_world_age=state.universe.age_years - (420 - index * 47),
            status=SpeciesStatus.STABLE,
            generation=1,
            parent_species_id=None,
            traits=Traits(
                efficiency=round(0.38 + rng.random() * 0.42, 3),
                adaptation=round(0.36 + rng.random() * 0.42, 3),
                cooperation=round(0.28 + rng.random() * 0.44, 3),
                mobility=round(0.2 + rng.random() * 0.52, 3),
                resilience=round(0.3 + rng.random() * 0.5, 3),
            ),
        )
        state.species[species.id] = species

    for species in state.species.values():
        origin = state.regions[species.origin_region_id]
        for region in state.regions.values():
            distance = abs(region.x - origin.x) + abs(region.y - origin.y)
            if distance > 3:
                continue
            rng = stable_rng(state.seed, "population", species.id, region.id)
            habitat_score = (
                region.energy_level * species.traits.efficiency
                + region.resource_density * species.traits.adaptation
                + region.stability * species.traits.resilience
            ) / 3
            distance_penalty = max(0.15, 1 - distance * 0.24)
            count = int((1800 + rng.randint(0, 5200)) * habitat_score * distance_penalty)
            if count <= 80:
                continue
            state.populations[(species.id, region.id)] = Population(
                species_id=species.id,
                region_id=region.id,
                population_count=count,
                energy_consumption=round(0.1 + species.traits.efficiency * 0.28, 3),
                growth_rate=0.0,
                migration_pressure=0.0,
                last_updated_tick=state.universe.tick,
            )


def _seed_bootstrap_events(state: AlphaState) -> None:
    first_species = next(iter(state.species.values()))
    first_region = state.regions[first_species.origin_region_id]
    title, summary = event_templates.species_emerged(first_species, None, first_region)
    state.add_event(
        EventType.SPECIES_EMERGED,
        title,
        summary,
        severity=3,
        region_id=first_region.id,
        species_id=first_species.id,
        payload={"generation": first_species.generation},
    )

    mutation_species = list(state.species.values())[1]
    mutation_region = state.regions[mutation_species.origin_region_id]
    title, summary = event_templates.mutation_detected(mutation_species, mutation_region)
    state.add_event(
        EventType.MUTATION_DETECTED,
        title,
        summary,
        severity=2,
        region_id=mutation_region.id,
        species_id=mutation_species.id,
    )

    decline_species = list(state.species.values())[2]
    title, summary = event_templates.species_declined(decline_species, 18)
    state.add_event(
        EventType.SPECIES_DECLINED,
        title,
        summary,
        severity=3,
        region_id=decline_species.origin_region_id,
        species_id=decline_species.id,
        payload={"decline_percent": 18},
    )

    shift_region = state.regions["region-041"]
    title, summary = event_templates.region_resource_shift(shift_region, "rise")
    state.add_event(
        EventType.REGION_RESOURCE_SHIFT,
        title,
        summary,
        severity=2,
        region_id=shift_region.id,
        payload={"direction": "rise"},
    )

    collapse_region = state.regions["region-018"]
    collapse_region.collapsed = True
    title, summary = event_templates.region_collapse(collapse_region)
    state.add_event(
        EventType.REGION_COLLAPSE,
        title,
        summary,
        severity=5,
        region_id=collapse_region.id,
    )


def _recalculate_dominant_species(state: AlphaState) -> None:
    for region in state.regions.values():
        region_populations = [
            population
            for population in state.populations.values()
            if population.region_id == region.id and population.population_count > 0
        ]
        if not region_populations:
            region.dominant_species_id = None
            continue
        region.dominant_species_id = max(
            region_populations,
            key=lambda population: population.population_count,
        ).species_id


def region_distance(a: Region, b: Region) -> int:
    return int(math.fabs(a.x - b.x) + math.fabs(a.y - b.y))
