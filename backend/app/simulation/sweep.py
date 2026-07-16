"""Sweep chirality rules over a parameter grid × seed ensemble.

Deterministic CLI for re-running doc examples and measuring parameter sensitivity.
See docs/CHIRALITY_AND_MIND.md for context.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from typing import Any

from app.domain import Era
from app.simulation import DEFAULT_SIMULATION_RULES, SimulationEngine, seed_alpha
from app.simulation.diagnostics import _spread


def run_sweep(
    *,
    param: str = "field_strength",
    values: list[float] | None = None,
    seed: int = 4211,
    seeds: int = 8,
    ticks: int = 600,
) -> dict[str, Any]:
    """Sweep one chirality parameter over values × ensemble; return sweep results.

    Each (value, ensemble_member) run is deterministic: the same inputs always
    produce the same outputs, with no randomness or wall-clock time leaking into
    the state.
    """
    if values is None:
        values = _default_values(param)

    rows: list[dict[str, Any]] = []
    for value in values:
        row = _sweep_value(
            param=param,
            value=value,
            base_seed=seed,
            seeds=seeds,
            ticks=ticks,
        )
        rows.append(row)

    return {
        "param": param,
        "seed": seed,
        "seeds": [seed + offset for offset in range(max(1, seeds))],
        "ticks": ticks,
        "rows": rows,
    }


def _default_values(param: str) -> list[float]:
    """Default parameter values for sweeps."""
    if param == "racemization_rate":
        return [0, 0.008, 0.012, 0.016, 0.02, 0.03, 0.06, 0.08]
    # field_strength and others default
    return [0, 0.001, 0.002, 0.005, 0.01]


def _sweep_value(
    *,
    param: str,
    value: float,
    base_seed: int,
    seeds: int,
    ticks: int,
) -> dict[str, Any]:
    """Run one value across the ensemble; aggregate and return results."""
    ensemble = [base_seed + offset for offset in range(max(1, seeds))]
    runs: list[dict[str, Any]] = []

    for member in ensemble:
        run_result = _run_single(
            param=param,
            value=value,
            seed=member,
            ticks=ticks,
        )
        runs.append(run_result)

    return _aggregate_runs(value, runs)


def _run_single(
    *,
    param: str,
    value: float,
    seed: int,
    ticks: int,
) -> dict[str, Any]:
    """Execute one (param, value, seed) run; return measurements."""
    # Build rules with the swept parameter.
    rules = replace(
        DEFAULT_SIMULATION_RULES,
        chirality=replace(
            DEFAULT_SIMULATION_RULES.chirality,
            **{param: value},
        ),
    )

    # Initialize and advance the simulation.
    state = seed_alpha(seed=seed)
    engine = SimulationEngine(seed=seed, rules=rules)

    era_tick = None
    lock_tick = None

    for _ in range(ticks):
        engine.advance(state, ticks=1)

        # Check for Stabilization era (first time).
        if era_tick is None and state.universe.current_era == Era.STABILIZATION:
            era_tick = state.universe.tick

        # Check for all non-collapsed regions locked (first time).
        if lock_tick is None:
            non_collapsed = [r for r in state.regions.values() if not r.collapsed]
            if non_collapsed and all(r.chirality_locked for r in non_collapsed):
                lock_tick = state.universe.tick

    # Record end-of-run measurements.
    locked_region_count = sum(
        1 for region in state.regions.values()
        if not region.collapsed and region.chirality_locked
    )

    return {
        "homochirality_index": state.universe.homochirality_index,
        "local_order_index": state.universe.local_order_index,
        "domain_count": state.universe.domain_count,
        "locked_regions": locked_region_count,
        "era_tick": era_tick,
        "lock_tick": lock_tick,
    }


def _aggregate_runs(value: float, runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate ensemble runs into spread statistics."""
    homochirality_values = [r["homochirality_index"] for r in runs]
    local_order_values = [r["local_order_index"] for r in runs]
    domain_count_values = [r["domain_count"] for r in runs]
    locked_regions_values = [r["locked_regions"] for r in runs]

    # era_tick and lock_tick: only consider runs that reached those milestones.
    era_ticks = [r["era_tick"] for r in runs if r["era_tick"] is not None]
    lock_ticks = [r["lock_tick"] for r in runs if r["lock_tick"] is not None]

    # Counters: how many runs hit these conditions.
    single_domain_count = sum(1 for r in runs if r["domain_count"] == 1)
    life_earned_count = sum(1 for r in runs if r["era_tick"] is not None)

    return {
        "value": value,
        "homochirality": _spread(homochirality_values),
        "localOrder": _spread(local_order_values),
        "domainCount": _spread(domain_count_values),
        "lockedRegions": _spread(locked_regions_values),
        "eraTick": _spread(era_ticks),
        "lockTick": _spread(lock_ticks),
        "singleDomain": {
            "count": single_domain_count,
            "total": len(runs),
            "ratio": round(single_domain_count / len(runs), 4) if runs else 0.0,
        },
        "lifeEarned": {
            "count": life_earned_count,
            "total": len(runs),
            "ratio": round(life_earned_count / len(runs), 4) if runs else 0.0,
        },
    }


def _print_human_report(sweep_result: dict[str, Any]) -> None:
    """Print a human-readable sweep report."""
    print("Evoverse Chirality Sweep")
    print(f"Parameter: {sweep_result['param']}")
    print(f"Base Seed: {sweep_result['seed']}")
    print(f"Ensemble: {len(sweep_result['seeds'])} seeds")
    print(f"Ticks per Run: {sweep_result['ticks']}")
    print()

    # Header
    print(
        f"{'Value':>8} | {'Homo Mean':>10} | {'Domain Mean':>12} | "
        f"{'Single':>10} | {'Life':>10} | {'Lock Mean':>10}"
    )
    print("-" * 85)

    # Data rows
    for row in sweep_result["rows"]:
        value = row["value"]
        homo_mean = row["homochirality"]["mean"]
        domain_mean = row["domainCount"]["mean"]
        single_ratio = row["singleDomain"]["ratio"]
        life_ratio = row["lifeEarned"]["ratio"]
        lock_mean = row["lockTick"]["mean"]

        # Format lock_mean as "N/A" if None
        lock_str = f"{lock_mean:>10.1f}" if lock_mean is not None else f"{'N/A':>10}"

        print(
            f"{value:>8.4f} | {homo_mean:>10.4f} | {domain_mean:>12.2f} | "
            f"{single_ratio:>10.4f} | {life_ratio:>10.4f} | {lock_str}"
        )


def _parse_csv_floats(raw: str) -> list[float]:
    """Parse comma-separated floats, skipping empty tokens."""
    values: list[float] = []
    for token in raw.split(","):
        token = token.strip()
        if token:
            values.append(float(token))
    return values


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sweep chirality rules over a parameter grid × seed ensemble."
    )
    parser.add_argument(
        "--param",
        default="field_strength",
        choices=["field_strength", "racemization_rate"],
        help="Chirality parameter to sweep (default: field_strength).",
    )
    parser.add_argument(
        "--values",
        type=_parse_csv_floats,
        default=None,
        help="Comma-separated values to sweep. Uses defaults if omitted.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=4211,
        help="Base seed for the ensemble (default: 4211).",
    )
    parser.add_argument(
        "--seeds",
        type=int,
        default=8,
        help="Ensemble size: number of consecutive seeds (default: 8).",
    )
    parser.add_argument(
        "--ticks",
        type=int,
        default=600,
        help="Ticks per run (default: 600).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON.",
    )

    args = parser.parse_args()

    result = run_sweep(
        param=args.param,
        values=args.values,
        seed=args.seed,
        seeds=args.seeds,
        ticks=args.ticks,
    )

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        _print_human_report(result)


if __name__ == "__main__":
    main()
