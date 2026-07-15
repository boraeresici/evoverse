from __future__ import annotations

from app.simulation import SimulationEngine, seed_alpha
from app.simulation.diagnostics import (
    DEFAULT_FIELDS,
    condition_vector,
    correlation_field,
    correlation_length,
    pattern_census,
    pattern_triggers,
    pattern_triggers_traced,
    scale_free_scan,
)


def _advanced_state(seed: int = 4211, ticks: int = 600):
    state = seed_alpha(seed=seed)
    SimulationEngine(seed=seed).advance(state, ticks=ticks)
    return state


# --- Part A: correlation length --------------------------------------------


def test_correlation_field_subtracts_the_mean_and_finds_a_crossing() -> None:
    state = _advanced_state()
    result = correlation_field(state, "stability")

    # C(0) is normalised to 1, so the first bucket is positive and c0 (the variance)
    # is strictly positive on a live world.
    assert result["c0"] > 0
    assert result["curve"], "expected a non-empty C(r) curve"
    # ξ is a real distance in the world, never negative.
    assert result["xi"] >= 0.0
    # The mean-subtraction constraint (∑ δφ = 0) forces C(r) to leave the positive
    # region: either it crosses zero (ξ interpolated) or it is flagged saturated.
    crosses = any(c < 0 for _, c in result["curve"])
    assert crosses or result["saturated"]


def test_correlation_length_covers_every_default_field() -> None:
    state = _advanced_state()
    result = correlation_length(state)
    assert set(result) == set(DEFAULT_FIELDS)
    for field_result in result.values():
        assert "xi" in field_result and "curve" in field_result


def test_correlation_is_deterministic() -> None:
    first = correlation_length(_advanced_state())
    second = correlation_length(_advanced_state())
    assert first == second


# --- scale-free scan --------------------------------------------------------


def test_scale_free_scan_reports_points_and_a_verdict() -> None:
    scan = scale_free_scan(
        4211, 300, sizes=[(12, 9), (16, 12), (20, 15)], field="stability"
    )
    assert [p["L"] for p in scan["points"]] == [12, 16, 20]
    assert scan["verdict"] in {
        "critical",
        "sub_critical",
        "super_critical",
        "intermediate",
        "insufficient",
    }
    for point in scan["points"]:
        assert point["xiOverL"] == round(point["xi"] / point["L"], 4)


def test_scale_free_scan_skips_unseedable_small_worlds() -> None:
    # 8x6 = 48 regions cannot host the seeder's fixed origins (up to region-101);
    # the scan records it as skipped instead of crashing.
    scan = scale_free_scan(4211, 100, sizes=[(8, 6), (12, 9)], field="stability")
    assert [p["L"] for p in scan["points"]] == [12]
    assert scan["skipped"] == [{"width": 8, "height": 6, "reason": "unseedable-size"}]


# --- Part B: pattern census -------------------------------------------------


def test_pattern_census_has_every_level_and_is_deterministic() -> None:
    state = _advanced_state()
    census = pattern_census(state)
    assert set(census) == {
        "morphotypes",
        "spatialMotifs",
        "domainSizePowerLaw",
        "lineageMotifs",
        "eventNgrams",
    }
    # distinct / effectiveCount are well-formed diversity numbers.
    morph = census["morphotypes"]
    assert morph["distinct"] >= 1
    assert 0.0 <= morph["convergenceIndex"] <= 1.0
    assert morph["effectiveCount"] <= morph["distinct"] + 1e-9
    # Deterministic.
    assert pattern_census(_advanced_state()) == census


def test_domain_sizes_sum_to_regions_with_a_dominant_species() -> None:
    state = _advanced_state()
    power = pattern_census(state)["domainSizePowerLaw"]
    total_in_domains = sum(size * count for size, count in power["histogram"])
    dominant_regions = sum(
        1 for region in state.regions.values() if region.dominant_species_id is not None
    )
    assert total_in_domains == dominant_regions


# --- Part C: conditional triggers -------------------------------------------


def test_pattern_triggers_instances_match_regions_with_a_dominant_species() -> None:
    state = _advanced_state()
    triggers = pattern_triggers(state)
    assert triggers["mode"] == "static"
    dominant_regions = sum(
        1 for region in state.regions.values() if region.dominant_species_id is not None
    )
    assert triggers["instances"] == dominant_regions
    for row in triggers["table"]:
        assert row["lift"] >= 0.0
        assert row["support"] >= 1


def test_condition_vector_is_a_readable_stable_string() -> None:
    state = _advanced_state()
    region = next(iter(sorted(state.regions.values(), key=lambda item: item.id)))
    condition = condition_vector(state, region)
    assert condition.startswith("era=")
    assert "stab=" in condition and "cat=" in condition


def test_pattern_triggers_traced_captures_emergence_conditions() -> None:
    traced = pattern_triggers_traced(4211, 400, step=100)
    assert traced["mode"] == "traced"
    assert traced["step"] == 100
    # Every stamped instance is a (pattern, condition) row feeding the lift table.
    assert traced["instances"] >= 1
    assert traced == pattern_triggers_traced(4211, 400, step=100)
