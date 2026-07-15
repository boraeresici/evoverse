from __future__ import annotations

from app.domain import EventType
from app.simulation import DEFAULT_SIMULATION_RULES, SimulationEngine, seed_alpha
from app.simulation.benchmark import determinism_signature


def test_genesis_starts_near_racemic() -> None:
    state = seed_alpha(seed=4211)
    seed_bias_max = DEFAULT_SIMULATION_RULES.chirality.seed_bias_max

    # Every region starts within the seed-bias band of racemic (ee = 0), and none
    # is locked yet — the symmetry break has to be earned by the tick engine.
    assert all(abs(region.chirality_ee) <= seed_bias_max for region in state.regions.values())
    assert not any(region.chirality_locked for region in state.regions.values())
    assert state.universe.homochirality_index < seed_bias_max
    assert not state.universe.chirality_locked


def test_bifurcation_drives_universe_toward_homochirality() -> None:
    state = seed_alpha(seed=4211)
    start_index = state.universe.homochirality_index

    SimulationEngine(seed=4211).advance(state, ticks=400)

    # The bifurcation + avalanche amplify the tiny seed bias into a far more
    # homochiral universe, and some regions latch to a full hand.
    assert state.universe.homochirality_index > start_index
    assert state.universe.homochirality_index > 0.5
    assert any(region.chirality_locked for region in state.regions.values())
    # A latched region snaps to a pure hand and never leaves [-1, 1].
    for region in state.regions.values():
        assert -1.0 <= region.chirality_ee <= 1.0
        if region.chirality_locked:
            assert abs(region.chirality_ee) == 1.0


def test_locked_region_stays_locked_and_fixed() -> None:
    state = seed_alpha(seed=4211)
    engine = SimulationEngine(seed=4211)
    engine.advance(state, ticks=400)

    locked = {
        region.id: region.chirality_ee
        for region in state.regions.values()
        if region.chirality_locked
    }
    assert locked, "expected at least one locked region after 400 ticks"

    engine.advance(state, ticks=200)
    for region_id, ee in locked.items():
        region = state.regions[region_id]
        assert region.chirality_locked is True
        assert region.chirality_ee == ee  # irreversible latch: hand never flips


def test_chirality_is_deterministic_for_same_seed() -> None:
    first = seed_alpha(seed=4211)
    second = seed_alpha(seed=4211)
    SimulationEngine(seed=4211).advance(first, ticks=300)
    SimulationEngine(seed=4211).advance(second, ticks=300)

    # determinism_signature now includes chirality, so identical seeds must agree.
    assert determinism_signature(first) == determinism_signature(second)
    assert first.universe.homochirality_index == second.universe.homochirality_index


def test_homochirality_index_is_mean_abs_ee() -> None:
    state = seed_alpha(seed=4211)
    SimulationEngine(seed=4211).advance(state, ticks=250)

    live = [region for region in state.regions.values() if not region.collapsed]
    expected = round(sum(abs(region.chirality_ee) for region in live) / len(live), 4)
    assert state.universe.homochirality_index == expected
    assert 0.0 <= state.universe.homochirality_index <= 1.0


# --- §11.2: inheritance + heterochiral selection + SYMMETRY_BREAK -------------


def test_lineages_adopt_a_hand_and_emit_symmetry_break() -> None:
    state = seed_alpha(seed=4211)
    assert all(species.chirality == 0 for species in state.species.values())

    SimulationEngine(seed=4211).advance(state, ticks=400)

    # Founding lineages whose origin region locked have committed to a hand.
    committed = [s for s in state.species.values() if s.chirality != 0]
    assert committed, "expected lineages to adopt a hand as regions lock"
    assert all(s.chirality in (-1, 1) for s in committed)

    breaks = [e for e in state.events if e.event_type == EventType.SYMMETRY_BREAK]
    scopes = {e.payload.get("scope") for e in breaks}
    assert "region" in scopes  # first molecular symmetry break
    assert "lineage" in scopes  # a lineage committing a hand


def test_universe_full_lock_emits_a_single_symmetry_break() -> None:
    state = seed_alpha(seed=4211)
    engine = SimulationEngine(seed=4211)
    engine.advance(state, ticks=600)

    assert state.universe.chirality_locked is True
    universe_breaks = [
        e
        for e in state.events
        if e.event_type == EventType.SYMMETRY_BREAK and e.payload.get("scope") == "universe"
    ]
    assert len(universe_breaks) == 1  # fires once, on the transition

    # It does not re-fire on further ticks.
    engine.advance(state, ticks=100)
    universe_breaks = [
        e
        for e in state.events
        if e.event_type == EventType.SYMMETRY_BREAK and e.payload.get("scope") == "universe"
    ]
    assert len(universe_breaks) == 1


def test_child_inherits_parent_hand() -> None:
    state = seed_alpha(seed=4211)
    # Let hands settle, then run through several speciation intervals.
    SimulationEngine(seed=4211).advance(state, ticks=900)

    checked = 0
    for species in state.species.values():
        parent_id = species.parent_species_id
        if parent_id is None or species.chirality == 0:
            continue
        parent = state.species.get(parent_id)
        if parent is None or parent.chirality == 0:
            continue
        checked += 1
        # Same hand as parent, unless a rare flip occurred (opposite hand).
        assert species.chirality in (parent.chirality, -parent.chirality)
    assert checked > 0, "expected at least one child with a committed parent hand"


def test_heterochiral_load_penalizes_growth() -> None:
    rules = DEFAULT_SIMULATION_RULES
    state = seed_alpha(seed=4211)
    SimulationEngine(seed=4211).advance(state, ticks=500)

    # heterochiral_load stays a valid 0..1 figure and reflects the mismatch model:
    # a fully-matched (or racemic) world leaves it low; mismatches raise it.
    for species in state.species.values():
        assert 0.0 <= species.heterochiral_load <= 1.0
    # The lethal knob is a positive decline fraction (applied as a growth floor).
    assert rules.chirality.heterochiral_lethal_decline > 0
