from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import replace

from app.domain import (
    EVENT_PAYLOAD_SCHEMA_VERSION,
    CatalystActionType,
    EventType,
    SpeciesStatus,
    event_payload_schema,
    validate_event_payload,
)
from app.simulation import DEFAULT_SIMULATION_RULES, SimulationEngine, seed_alpha
from app.simulation.benchmark import determinism_signature, run_benchmark


def test_seeded_alpha_has_phase_one_shape() -> None:
    state = seed_alpha(seed=4211)

    assert state.universe.id == "alpha"
    assert len(state.regions) >= 100
    assert len(state.species) >= 6
    assert len(state.populations) > len(state.species)


def test_simulation_generates_mvp_event_types() -> None:
    state = seed_alpha(seed=4211)
    SimulationEngine(seed=4211).advance(state, ticks=120)
    event_types = {event.event_type for event in state.events}

    assert {
        EventType.SPECIES_EMERGED,
        EventType.SPECIES_DECLINED,
        EventType.MUTATION_DETECTED,
        EventType.REGION_RESOURCE_SHIFT,
        EventType.REGION_COLLAPSE,
    }.issubset(event_types)


def _rules_without_consumption() -> object:
    """Rules with the consumer-resource coupling switched off — the pre-23.6
    behaviour, where a region drifted on its own noise no matter what lived in
    it. A scale this large makes every draw round to nothing."""
    return replace(
        DEFAULT_SIMULATION_RULES,
        region=replace(DEFAULT_SIMULATION_RULES.region, consumption_pressure_scale=10**12),
    )


def _busiest_region(state) -> str:
    """The region under the heaviest draw — sum(population * energy_consumption)."""
    draw: dict[str, float] = defaultdict(float)
    for population in state.populations.values():
        draw[population.region_id] += (
            population.population_count * population.energy_consumption
        )
    return max(sorted(draw), key=lambda region_id: draw[region_id])


def test_populations_draw_down_the_region_they_live_in() -> None:
    """`Population.energy_consumption` was computed, stored and served, and read
    by nothing: life could not touch its own world. One tick is enough to show
    the loop is closed, because region drift is seeded per (seed, tick, region)
    and so is identical between these two runs apart from the draw."""
    with_life = seed_alpha(seed=4211)
    without_life = seed_alpha(seed=4211)
    # The busiest region, not just any: `resource_density` is rounded to 3dp each
    # tick, so a thin region's draw rounds to nothing on any single tick and only
    # tells over many. See `consumption_pressure_scale` on the region rules.
    populated = _busiest_region(without_life)
    for population in without_life.populations.values():
        if population.region_id == populated:
            population.population_count = 0

    SimulationEngine(seed=4211).advance(with_life, ticks=1)
    SimulationEngine(seed=4211).advance(without_life, ticks=1)

    assert (
        with_life.regions[populated].resource_density
        < without_life.regions[populated].resource_density
    )


def test_a_lineage_pays_for_the_neighbour_sharing_its_region() -> None:
    """Interspecific competition, which the engine never modelled directly.
    Populations only ever read their region's E/R/S and their own count, so two
    species in one region could not see each other. Now they drink from the same
    well: the draw is summed over every population in the region, so a
    neighbour's headcount lands in your habitat fit as a lower resource density.
    Nothing here is a competition rule — it falls out of the resource."""
    crowded = seed_alpha(seed=4211)
    alone = seed_alpha(seed=4211)
    region_id = _busiest_region(crowded)  # thin regions round their draw away
    species_ids = sorted(
        population.species_id
        for population in crowded.populations.values()
        if population.region_id == region_id and population.population_count > 0
    )
    assert len(species_ids) > 1, "need a shared region to show competition"
    survivor, *neighbours = species_ids
    for neighbour in neighbours:
        alone.populations[(neighbour, region_id)].population_count = 0

    SimulationEngine(seed=4211).advance(crowded, ticks=200)
    SimulationEngine(seed=4211).advance(alone, ticks=200)

    # Same lineage, same region, same ticks, same rng — the only difference is who
    # else was drinking. Its well stays fuller and it ends up more numerous with
    # the region to itself. (200 ticks, not 1: a single tick's difference is
    # ~3e-5 of growth and rounds away — the cost is real but it accrues.)
    assert (
        alone.regions[region_id].resource_density
        > crowded.regions[region_id].resource_density
    )
    assert (
        alone.populations[(survivor, region_id)].population_count
        > crowded.populations[(survivor, region_id)].population_count
    )


def test_consumption_bounds_population_instead_of_letting_it_run() -> None:
    """A carrying capacity, which the model had no mechanism for: density
    pressure throttled a population by its *own* size, but nothing tied the
    ceiling to the world. Unbounded growth is what that produced."""
    bounded = seed_alpha(seed=4211)
    unbounded = seed_alpha(seed=4211)
    SimulationEngine(seed=4211).advance(bounded, ticks=2000)
    SimulationEngine(seed=4211, rules=_rules_without_consumption()).advance(
        unbounded, ticks=2000
    )

    def total(state) -> int:
        return sum(p.population_count for p in state.populations.values())

    assert total(bounded) < total(unbounded)
    mean_resource = sum(r.resource_density for r in bounded.regions.values()) / len(
        bounded.regions
    )
    unbounded_mean = sum(r.resource_density for r in unbounded.regions.values()) / len(
        unbounded.regions
    )
    assert mean_resource < unbounded_mean  # the world is visibly grazed


def test_the_chronicle_is_its_own_world_not_a_metronome() -> None:
    """91% of the chronicle used to be three scripted beats — a resource shift
    every 13 ticks, a decline every 17, a collapse every 151 — because the organic
    rules they covered for fired *zero* times in 10,000 ticks. Their thresholds
    described trends but were compared against the previous tick, which no world
    this slow can satisfy. Now the same thresholds are read against the last
    reported value, and collapse answers to depletion, so Alpha files its own news
    and no event is scripted."""
    state = seed_alpha(seed=4211)
    SimulationEngine(seed=4211).advance(state, ticks=2000)
    counts = Counter(event.event_type for event in state.events)

    assert counts[EventType.REGION_RESOURCE_SHIFT] > 100
    assert counts[EventType.SPECIES_DECLINED] > 100
    # No beat is left: nothing in the chronicle is a clock wearing an event's name.
    scripted = [e for e in state.events if e.payload.get("synthetic")]
    assert scripted == []


def test_a_reported_decline_is_one_the_population_actually_took() -> None:
    """The 17-tick beat announced that a species had lost 14% of its population
    and then did not touch the population — 588 times per 10,000 ticks, including
    61 about species that were already extinct and 257 about species that *grew*
    that tick. Every decline in the chronicle now has to have happened."""
    state = seed_alpha(seed=4211)
    engine = SimulationEngine(seed=4211)
    seen: set[str] = set()
    for _ in range(600):
        before = {key: p.population_count for key, p in state.populations.items()}
        engine.advance(state, ticks=1)
        for event in state.events:
            if event.event_type != EventType.SPECIES_DECLINED or event.id in seen:
                continue
            seen.add(event.id)
            counts = [
                (before.get(key, 0), p.population_count)
                for key, p in state.populations.items()
                if p.species_id == event.species_id and p.region_id == event.region_id
            ]
            assert counts, "a decline was reported for a population that is not there"
            was, now = counts[0]
            assert now < was, f"{event.species_id} was reported declining while at {was}->{now}"

    assert seen, "expected the world to report declines of its own"


def test_a_slow_slide_is_reported_once_not_every_tick() -> None:
    """The reference resets on report, so a region grinding downward is told once
    per threshold-worth of movement. Without that reset, reporting against
    anything but the previous tick would flood the chronicle — 16,411 shifts per
    10,000 ticks at the old 0.16."""
    state = seed_alpha(seed=4211)
    region = state.regions["region-001"]
    threshold = DEFAULT_SIMULATION_RULES.region.resource_shift_threshold
    region.resource_density = 0.9
    region.last_reported_resource_density = 0.9

    engine = SimulationEngine(seed=4211)
    engine.advance(state, ticks=1)
    shifts = lambda: [  # noqa: E731
        e
        for e in state.events
        if e.event_type == EventType.REGION_RESOURCE_SHIFT and e.region_id == "region-001"
    ]
    assert not shifts()  # one tick cannot move it a threshold's worth

    region.resource_density = round(0.9 - threshold, 3)
    engine.advance(state, ticks=1)
    assert len(shifts()) == 1
    # The report moved the reference down with it: sitting there is not news again.
    assert region.last_reported_resource_density == region.resource_density
    engine.advance(state, ticks=5)
    assert len(shifts()) == 1


def _living_species_with_populations(state):
    return next(
        species
        for species in state.species.values()
        if species.status != SpeciesStatus.EXTINCT
        and any(pop.species_id == species.id for pop in state.populations.values())
    )


def _pin_to_floor(state, species, count: int) -> None:
    """Collapse a lineage onto a single population holding ``count`` individuals."""
    pops = [pop for pop in state.populations.values() if pop.species_id == species.id]
    for pop in pops[1:]:
        pop.population_count = 0
    pops[0].population_count = count


def test_a_dip_to_the_floor_is_a_grace_not_an_instant_extinction() -> None:
    """Touching the extinction floor no longer writes a lineage off on the spot.
    It enters a refugium grace — still alive, still simulated — and if its habitat
    lifts it back above the floor it keeps living."""
    state = seed_alpha(seed=4211)
    engine = SimulationEngine(seed=4211)
    floor = engine.rules.species_status.extinct_population
    species = _living_species_with_populations(state)

    _pin_to_floor(state, species, floor)
    engine._update_species_statuses(state)
    assert species.status != SpeciesStatus.EXTINCT
    assert species.extinction_grace_ticks == 1

    # The habitat recovers before the grace runs out.
    _pin_to_floor(state, species, floor + 500)
    engine._update_species_statuses(state)
    assert species.status != SpeciesStatus.EXTINCT
    assert species.extinction_grace_ticks == 0


def test_a_collapse_that_outlasts_the_grace_ends_and_zeroes_the_lineage() -> None:
    """A lineage held at the floor for the whole grace window is finalised extinct,
    and its residual count is zeroed — extinction and population agree."""
    state = seed_alpha(seed=4211)
    engine = SimulationEngine(seed=4211)
    rules = engine.rules.species_status
    species = _living_species_with_populations(state)

    for _ in range(rules.relict_grace_ticks):
        _pin_to_floor(state, species, rules.extinct_population)
        engine._update_species_statuses(state)

    assert species.status == SpeciesStatus.EXTINCT
    remaining = sum(
        pop.population_count
        for pop in state.populations.values()
        if pop.species_id == species.id
    )
    assert remaining == 0


def test_an_extinct_lineage_is_never_left_frozen_at_the_floor() -> None:
    """The bug behind 'extinct / 12 population': an extinct lineage used to keep the
    count it died holding, so the title said 12 while the field said 0. Extinction
    now zeroes it on the next status pass, legacy remnants included."""
    state = seed_alpha(seed=4211)
    engine = SimulationEngine(seed=4211)
    species = _living_species_with_populations(state)
    species.status = SpeciesStatus.EXTINCT
    _pin_to_floor(state, species, 12)

    engine._update_species_statuses(state)

    remaining = sum(
        pop.population_count
        for pop in state.populations.values()
        if pop.species_id == species.id
    )
    assert remaining == 0
    assert species.status == SpeciesStatus.EXTINCT


def _colonisation_engine(chance: float) -> SimulationEngine:
    rules = replace(
        DEFAULT_SIMULATION_RULES,
        colonization=replace(DEFAULT_SIMULATION_RULES.colonization, colonization_chance=chance),
    )
    return SimulationEngine(seed=4211, rules=rules)


def _make_vacant_habitable_region_next_to_a_source(state, engine):
    """Set up a strong source population next to an emptied, habitable region.
    Returns the vacant target region."""
    rules = engine.rules.colonization
    source = max(state.populations.values(), key=lambda pop: pop.population_count)
    source.population_count = rules.min_source_population + rules.founder_population + 200
    source_region = state.regions[source.region_id]

    target = next(
        region
        for region in state.regions.values()
        if abs(region.x - source_region.x) + abs(region.y - source_region.y) == 1
    )
    for population in state.populations.values():
        if population.region_id == target.id:
            population.population_count = 0
    target.collapsed = False
    target.energy_level = 0.9
    target.resource_density = 0.9
    target.stability = 0.9
    target.chirality_ee = 0.0  # racemic target: no lineage is wrong-handed here
    return target


def test_a_vacant_habitable_region_is_recolonised_from_a_neighbour() -> None:
    """Conway-style pull: an empty but viable niche draws colonists from a living
    neighbour, so a region that lost its life comes back rather than staying dead."""
    state = seed_alpha(seed=4211)
    engine = _colonisation_engine(chance=1.0)  # certain, for a deterministic test
    target = _make_vacant_habitable_region_next_to_a_source(state, engine)

    before = len(state.events)
    engine._colonize_empty_regions(state)

    target_population = sum(
        pop.population_count
        for pop in state.populations.values()
        if pop.region_id == target.id
    )
    assert target_population > 0
    colonized = [
        event
        for event in state.events[before:]
        if event.event_type == EventType.REGION_COLONIZED
    ]
    assert colonized and colonized[0].region_id == target.id


def test_colonisation_can_be_switched_off() -> None:
    """colonization_chance = 0 disables recolonisation entirely."""
    state = seed_alpha(seed=4211)
    engine = _colonisation_engine(chance=0.0)
    target = _make_vacant_habitable_region_next_to_a_source(state, engine)

    before = len(state.events)
    engine._colonize_empty_regions(state)

    assert not [
        event
        for event in state.events[before:]
        if event.event_type == EventType.REGION_COLONIZED
    ]
    target_population = sum(
        pop.population_count
        for pop in state.populations.values()
        if pop.region_id == target.id
    )
    assert target_population == 0


def test_colonisation_cannot_restart_a_map_with_no_life_left() -> None:
    """Colonisation refills niches while life exists somewhere; it cannot conjure
    life from an empty map. That boundary is exactly what re-origination (Layer B)
    is for — this test pins it so the two layers stay distinct."""
    state = seed_alpha(seed=4211)
    engine = _colonisation_engine(chance=1.0)
    for population in state.populations.values():
        population.population_count = 0
    for region in state.regions.values():
        region.collapsed = False
        region.energy_level = 0.6
        region.resource_density = 0.6
        region.stability = 0.6

    before = len(state.events)
    engine._colonize_empty_regions(state)

    assert not [
        event
        for event in state.events[before:]
        if event.event_type == EventType.REGION_COLONIZED
    ]


def test_simulation_is_deterministic_for_same_seed() -> None:
    first = seed_alpha(seed=4211)
    second = seed_alpha(seed=4211)

    SimulationEngine(seed=4211).advance(first, ticks=80)
    SimulationEngine(seed=4211).advance(second, ticks=80)

    first_signature = _signature(first)
    second_signature = _signature(second)

    assert first_signature == second_signature


def test_engine_uses_configured_catalyst_rules() -> None:
    rules = replace(
        DEFAULT_SIMULATION_RULES,
        catalyst=replace(
            DEFAULT_SIMULATION_RULES.catalyst,
            effect_ticks=2,
            strength=0.31,
        ),
    )
    state = seed_alpha(seed=4211)
    engine = SimulationEngine(seed=4211, rules=rules)

    action = engine.register_catalyst_action(
        state,
        region_id="region-001",
        action_type=CatalystActionType.ENERGY_PULSE,
    )

    assert action.expires_at_tick == state.universe.tick + 2
    assert action.strength == 0.31


def test_catalyst_downstream_events_include_observer_metadata() -> None:
    rules = replace(
        DEFAULT_SIMULATION_RULES,
        catalyst=replace(
            DEFAULT_SIMULATION_RULES.catalyst,
            strength=0.42,
        ),
    )
    state = seed_alpha(seed=4211)
    engine = SimulationEngine(seed=4211, rules=rules)

    engine.register_catalyst_action(
        state,
        region_id="region-001",
        action_type=CatalystActionType.RESOURCE_BURST,
        user_id="observer-catalyst",
    )
    engine.advance(state, ticks=1)

    downstream_events = [
        event
        for event in state.events
        if "observer-catalyst" in event.payload.get("catalyst_user_ids", [])
    ]

    assert downstream_events
    assert downstream_events[0].payload["catalyst_action_types"] == ["resource_burst"]


def test_simulation_events_have_versioned_payload_contracts() -> None:
    state = seed_alpha(seed=4211)
    engine = SimulationEngine(seed=4211)
    engine.register_catalyst_action(
        state,
        region_id="region-001",
        action_type=CatalystActionType.ENERGY_PULSE,
    )
    engine.advance(state, ticks=160)

    assert {event.event_type for event in state.events}.issuperset(
        {
            EventType.SPECIES_EMERGED,
            EventType.SPECIES_DECLINED,
            EventType.MUTATION_DETECTED,
            EventType.REGION_RESOURCE_SHIFT,
            EventType.REGION_COLLAPSE,
            EventType.CATALYST_ACTION,
        }
    )
    for event in state.events:
        assert event.payload["schemaVersion"] == EVENT_PAYLOAD_SCHEMA_VERSION
        assert event.payload["schema"] == event_payload_schema(event.event_type)
        assert event.payload["eventType"] == event.event_type.value
        assert validate_event_payload(event.event_type, event.payload) == []


def test_benchmark_report_contract() -> None:
    report = run_benchmark(seed=4211, ticks=80)

    assert report["seed"] == 4211
    assert report["ticks"] == 80
    assert report["finalTick"] == 80
    assert report["regionCount"] >= 100
    assert report["speciesCount"] >= 6
    assert report["eventCount"] >= 5
    assert report["collapsedRegionCount"] >= 0
    assert report["ticksPerSecond"] > 0
    assert len(report["determinismSignature"]) == 64
    assert report["topSpecies"]
    assert "species_emerged" in report["eventCounts"]


def test_benchmark_determinism_signature_is_stable() -> None:
    first = seed_alpha(seed=4211)
    second = seed_alpha(seed=4211)

    SimulationEngine(seed=4211).advance(first, ticks=80)
    SimulationEngine(seed=4211).advance(second, ticks=80)

    assert determinism_signature(first) == determinism_signature(second)


def test_long_run_keeps_alpha_viable() -> None:
    state = seed_alpha(seed=4211)
    SimulationEngine(seed=4211).advance(state, ticks=2000)

    collapsed_regions = sum(1 for region in state.regions.values() if region.collapsed)
    total_population = sum(
        population.population_count for population in state.populations.values()
    )

    assert collapsed_regions < len(state.regions) // 3
    assert total_population > 50_000
    assert len(state.species) < 80
    assert state.universe.stability_index > 0.35


def _signature(state) -> tuple:
    event_counts = Counter(event.event_type.value for event in state.events)
    species_totals = {}
    for population in state.populations.values():
        species_totals[population.species_id] = (
            species_totals.get(population.species_id, 0) + population.population_count
        )
    return (
        state.universe.age_years,
        state.universe.stability_index,
        len(state.regions),
        len(state.species),
        tuple(sorted(event_counts.items())),
        tuple(sorted(species_totals.items())[:12]),
    )
