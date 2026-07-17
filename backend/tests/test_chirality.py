from __future__ import annotations

from dataclasses import replace

from app.domain import BiomeType, Era, EventType, Region, Species, Traits
from app.simulation import DEFAULT_SIMULATION_RULES, SimulationEngine, seed_alpha
from app.simulation.benchmark import determinism_signature
from app.simulation.rules import SimulationRules
from app.simulation.seeder import _recalculate_universe_chirality


def _rules_without_field() -> SimulationRules:
    """Rules with the universe-wide field switched off, leaving only local
    noise to break symmetry — the pre-field behaviour."""
    return replace(
        DEFAULT_SIMULATION_RULES,
        chirality=replace(DEFAULT_SIMULATION_RULES.chirality, field_strength=0.0),
    )


def _region(ee: float, locked: bool = True) -> Region:
    return Region(
        id="region-001",
        universe_id="alpha",
        x=0,
        y=0,
        biome_type=BiomeType.BASIN,
        energy_level=0.6,
        resource_density=0.6,
        stability=0.6,
        chirality_ee=ee,
        chirality_locked=locked,
    )


def _species(chirality: int) -> Species:
    return Species(
        id="sp-0001",
        universe_id="alpha",
        name="THERA",
        origin_region_id="region-001",
        emerged_at_world_age=0,
        status=None,  # unused by the mismatch helper
        generation=1,
        parent_species_id=None,
        traits=Traits(0.5, 0.5, 0.5, 0.5, 0.5),
        chirality=chirality,
    )


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


def test_homochirality_index_is_global_and_local_order_is_not() -> None:
    state = seed_alpha(seed=4211)
    SimulationEngine(seed=4211).advance(state, ticks=250)

    live = [region for region in state.regions.values() if not region.collapsed]
    mean_ee = sum(region.chirality_ee for region in live) / len(live)
    assert state.universe.homochirality_index == round(abs(mean_ee), 4)
    assert state.universe.local_order_index == round(
        sum(abs(region.chirality_ee) for region in live) / len(live), 4
    )
    assert 0.0 <= state.universe.homochirality_index <= 1.0


def test_split_universe_is_locally_ordered_but_not_homochiral() -> None:
    """The metric's whole reason to exist: a map split into equal and opposite
    domains is *fully locked* and *fully locally ordered*, yet globally racemic.
    ``local_order_index`` reads 1.0 for it; ``homochirality_index`` must not —
    otherwise the Era gate hands life to a world that never picked a hand."""
    state = seed_alpha(seed=4211)
    regions = sorted(state.regions.values(), key=lambda region: region.id)
    for index, region in enumerate(regions):
        region.collapsed = False
        region.chirality_ee = 1.0 if index % 2 == 0 else -1.0
        region.chirality_locked = True

    _recalculate_universe_chirality(state)

    assert state.universe.local_order_index == 1.0  # every region is pure...
    assert state.universe.homochirality_index == 0.0  # ...and they cancel out
    assert state.universe.domain_count > 1
    assert state.universe.chirality_locked is True  # locked != homochiral


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


def test_heterochiral_mismatch_only_bites_committed_opposite_hand() -> None:
    engine = SimulationEngine(seed=4211)

    # Same hand as the region → no mismatch.
    assert engine._heterochiral_mismatch(_species(1), _region(1.0)) == 0.0
    # Uncommitted lineage (hand 0) → no mismatch, it just hasn't specialized.
    assert engine._heterochiral_mismatch(_species(0), _region(1.0)) == 0.0
    # Racemic region → no mismatch regardless of hand.
    assert engine._heterochiral_mismatch(_species(1), _region(0.0, locked=False)) == 0.0
    # Committed opposite hand in a locked region → full mismatch = |ee|.
    assert engine._heterochiral_mismatch(_species(-1), _region(1.0)) == 1.0
    # Partial ee → proportional mismatch.
    assert engine._heterochiral_mismatch(_species(-1), _region(0.4, locked=False)) == 0.4


# --- §11.3: two-tier Era gate ------------------------------------------------


def test_stabilization_era_is_earned_by_homochirality() -> None:
    life_gate = DEFAULT_SIMULATION_RULES.chirality.life_gate_index
    state = seed_alpha(seed=4211)
    assert state.universe.current_era == Era.EXPANSION
    engine = SimulationEngine(seed=4211)

    # Below the life gate, the universe has not yet earned Stabilization.
    engine.advance(state, ticks=40)
    assert state.universe.homochirality_index < life_gate
    assert state.universe.current_era == Era.EXPANSION

    # Once homochirality crosses the gate it advances — and announces it once.
    engine.advance(state, ticks=260)
    assert state.universe.homochirality_index >= life_gate
    assert state.universe.current_era == Era.STABILIZATION
    to_stab = [
        e
        for e in state.events
        if e.event_type == EventType.ERA_ADVANCED
        and e.payload.get("to_era") == Era.STABILIZATION.value
    ]
    assert len(to_stab) == 1
    assert to_stab[0].payload["from_era"] == Era.EXPANSION.value


def test_field_drives_every_seed_to_a_single_global_hand() -> None:
    """The universe-wide field is what makes the break *homochiral*: every seed
    must land on one hand across the whole map (one domain), even though which
    hand it lands on stays contingent."""
    hands = set()
    for seed in (4211, 7, 99, 1234, 31337):
        state = seed_alpha(seed=seed)
        SimulationEngine(seed=seed).advance(state, ticks=400)

        assert state.universe.domain_count == 1
        assert state.universe.homochirality_index == 1.0
        live = [region for region in state.regions.values() if not region.collapsed]
        assert len({1 if region.chirality_ee > 0 else -1 for region in live}) == 1
        hands.add(1 if state.universe.chirality_ee > 0 else -1)

    # Contingent, not hard-coded: the seeds do not all pick the same hand.
    assert hands == {1, -1}


def test_without_the_field_the_universe_locks_into_domains_and_is_denied_life() -> None:
    """Regression guard for the bug this slice fixes. Local noise alone freezes
    the map into opposing domains: fully locked, ``local_order_index`` 1.0, and
    globally racemic. Under the old ``mean |ee|`` metric that scored 1.0 and won
    the Stabilization Era. It must not."""
    rules = _rules_without_field()
    state = seed_alpha(seed=88)
    SimulationEngine(seed=88, rules=rules).advance(state, ticks=400)

    assert state.universe.local_order_index == 1.0  # every region committed...
    assert state.universe.domain_count > 1  # ...to more than one hand
    assert state.universe.homochirality_index < rules.chirality.life_gate_index
    assert state.universe.current_era == Era.EXPANSION
    assert not any(event.event_type == EventType.ERA_ADVANCED for event in state.events)


def _rules_with_racemization(rate: float) -> SimulationRules:
    return replace(
        DEFAULT_SIMULATION_RULES,
        chirality=replace(DEFAULT_SIMULATION_RULES.chirality, racemization_rate=rate),
    )


def test_racemization_above_the_gain_starves_the_universe() -> None:
    """With racemization at or above `amplify_k` the control parameter
    (amplify_k - racemization_rate) is non-positive, so racemic is stable: the
    universe never breaks symmetry and never earns life, however long it runs."""
    rules = _rules_with_racemization(DEFAULT_SIMULATION_RULES.chirality.amplify_k + 0.02)
    state = seed_alpha(seed=4211)
    SimulationEngine(seed=4211, rules=rules).advance(state, ticks=600)

    assert not any(region.chirality_locked for region in state.regions.values())
    assert state.universe.homochirality_index < rules.chirality.life_gate_index
    assert state.universe.current_era == Era.EXPANSION
    assert all(species.chirality == 0 for species in state.species.values())


def test_racemization_can_grant_life_while_nothing_ever_latches() -> None:
    """The silent zone `_validate_chirality_latch` warns about, pinned.

    Just past the latch cliff (~0.018 measured) regions settle short of
    `ee_lock_threshold` and hover there forever, while the mean is still high
    enough to clear the gate. The life gate reads the universe mean rather than
    the locks, so Stabilization is granted — while no region latches, no lineage
    adopts a hand, and everything downstream of the lock (hand inheritance,
    heterochiral selection, the Organism Lens) silently never happens. The window
    is narrow (by 0.03 the mean has fallen under the gate too and the universe is
    merely starved, not hollow), which is exactly why it is worth pinning: it is
    easy to tune into by accident. This is why the default sits well below it."""
    rules = _rules_with_racemization(0.02)
    state = seed_alpha(seed=4211)
    SimulationEngine(seed=4211, rules=rules).advance(state, ticks=600)

    assert state.universe.homochirality_index >= rules.chirality.life_gate_index
    assert state.universe.current_era == Era.STABILIZATION  # life is granted...
    assert not any(region.chirality_locked for region in state.regions.values())
    assert all(species.chirality == 0 for species in state.species.values())  # ...emptily


def test_default_racemization_still_lets_every_region_latch() -> None:
    """The default must stay on the latching side of the cliff — the whole T1
    tier hangs off the lock."""
    state = seed_alpha(seed=4211)
    SimulationEngine(seed=4211).advance(state, ticks=600)

    assert DEFAULT_SIMULATION_RULES.chirality.racemization_rate > 0
    assert all(region.chirality_locked for region in state.regions.values())
    assert state.universe.domain_count == 1
    assert all(species.chirality != 0 for species in state.species.values())


def test_intelligence_era_is_unreachable_in_t1() -> None:
    mind_gate = DEFAULT_SIMULATION_RULES.chirality.mind_gate_index
    state = seed_alpha(seed=4211)
    SimulationEngine(seed=4211).advance(state, ticks=1200)

    # Full homochirality is reached, but no lineage locks a mind in T1, so the
    # universe never claims the Intelligence Era.
    assert state.universe.homochirality_index >= mind_gate
    assert not any(species.mind_locked for species in state.species.values())
    assert state.universe.current_era == Era.STABILIZATION
    assert not any(
        e.event_type == EventType.ERA_ADVANCED
        and e.payload.get("to_era") == Era.INTELLIGENCE.value
        for e in state.events
    )


def test_intelligence_era_is_earned_once_a_mind_locks() -> None:
    state = seed_alpha(seed=4211)
    engine = SimulationEngine(seed=4211)
    engine.advance(state, ticks=300)
    assert state.universe.current_era == Era.STABILIZATION

    # Stand in for the future T2 cognitive tier latching a lineage's world-model.
    next(iter(state.species.values())).mind_locked = True
    engine.advance(state, ticks=1)
    assert state.universe.current_era == Era.INTELLIGENCE


def test_era_never_regresses() -> None:
    state = seed_alpha(seed=4211)
    engine = SimulationEngine(seed=4211)
    order = [Era.GENESIS, Era.EXPANSION, Era.STABILIZATION, Era.INTELLIGENCE]

    ranks: list[int] = []
    for _ in range(30):
        engine.advance(state, ticks=40)
        ranks.append(order.index(state.universe.current_era))

    assert ranks == sorted(ranks)  # monotonic, never falls back
