from __future__ import annotations

from app.simulation import SimulationEngine, seed_alpha
from app.simulation.diagnostics import (
    DEFAULT_FIELDS,
    _region_field_value,
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
    # The mean-subtraction constraint (∑ δφ = 0) forces C(r) below zero somewhere —
    # there is no "never crossed" outcome to fall back on.
    assert any(c < 0 for _, c in result["curve"])
    assert not result["degenerate"]


def test_correlation_field_obeys_the_cavagna_sum_rule() -> None:
    """The paper's constraint, and the reason a zero-crossing always exists.

    For fluctuations u (mean subtracted), Cavagna et al. give

        int_0^L dr sum_ij u_i.u_j delta(r - r_ij) = (sum_i u_i).(sum_j u_j) = 0

    correlation_field pairs each i<j once, so the same identity reads
    sum_{i<j} d_i d_j = -n*c0/2 — strictly negative, which is what forces C(r)
    below zero. If this drifts, ξ is measuring something other than correlation.
    """
    state = _advanced_state()
    regions = sorted(
        (r for r in state.regions.values() if not r.collapsed), key=lambda r: r.id
    )
    n = len(regions)
    for field in DEFAULT_FIELDS:
        values = [_region_field_value(state, region, field) for region in regions]
        mean = sum(values) / n
        deltas = [value - mean for value in values]
        c0 = sum(d * d for d in deltas) / n
        if c0 == 0:
            continue
        total = sum(
            deltas[i] * deltas[j]
            for i in range(n)
            for j in range(i + 1, n)
        )
        expected = -0.5 * n * c0
        assert abs(total - expected) / abs(expected) < 1e-9, field


def test_floored_xi_is_flagged_rather_than_reported_as_a_measurement() -> None:
    state = _advanced_state()
    for field in DEFAULT_FIELDS:
        result = correlation_field(state, field)
        if result["degenerate"]:
            continue
        first_r, first_c = result["curve"][0]
        # Already negative at the shortest distance means the crossing sits below
        # one lattice step: integer distances cannot resolve it, so ξ is a bound.
        assert result["xiFloored"] == (first_c < 0), field
        if result["xiFloored"]:
            assert result["xi"] == float(first_r), field


def test_correlation_field_ships_pair_counts_with_the_curve() -> None:
    state = _advanced_state()
    result = correlation_field(state, "stability")
    pairs = dict(result["pairs"])

    assert [r for r, _ in result["curve"]] == [r for r, _ in result["pairs"]]
    # Pair count collapses toward the lattice diagonal — that is the whole reason
    # the tail of C(r) is unreadable, so a consumer has to be able to see it.
    assert pairs[max(pairs)] < pairs[min(pairs)]
    assert sum(pairs.values()) == result["sampleSize"] * (result["sampleSize"] - 1) // 2


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
    # No "super_critical": the sum rule forbids the no-crossing state it keyed on.
    assert scan["verdict"] in {
        "critical",
        "sub_critical",
        "intermediate",
        "underpowered",
        "degenerate",
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


def test_pattern_triggers_cover_every_family() -> None:
    state = _advanced_state()
    triggers = pattern_triggers(state)
    assert triggers["mode"] == "static"
    families = triggers["families"]
    assert set(families) == {"spatial", "morphotype", "lineage"}

    # Spatial family: one instance per region with a dominant species.
    dominant_regions = sum(
        1 for region in state.regions.values() if region.dominant_species_id is not None
    )
    assert families["spatial"]["instances"] == dominant_regions

    # Morphotype & lineage families: one instance per species with a live origin
    # region — and every morphotype pattern is joined to a region-scoped condition.
    species_with_origin = sum(
        1 for species in state.species.values() if species.origin_region_id in state.regions
    )
    assert families["morphotype"]["instances"] == species_with_origin
    assert families["lineage"]["instances"] == species_with_origin
    for row in families["morphotype"]["table"]:
        assert row["pattern"].startswith("morphotype:")
        assert row["condition"].startswith("era=")  # region-level condition vector
        assert row["lift"] >= 0.0 and row["support"] >= 1


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
    families = traced["families"]
    assert set(families) == {"spatial", "morphotype"}
    # Spatial motifs appear over the run, and species emergences are event-joined to
    # their origin-region conditions.
    assert families["spatial"]["instances"] >= 1
    assert families["morphotype"]["instances"] >= 1
    # Deterministic replay: same inputs → identical output.
    assert traced == pattern_triggers_traced(4211, 400, step=100)
