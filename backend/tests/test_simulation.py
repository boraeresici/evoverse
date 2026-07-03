from __future__ import annotations

from collections import Counter
from dataclasses import replace

from app.domain import (
    EVENT_PAYLOAD_SCHEMA_VERSION,
    CatalystActionType,
    EventType,
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
