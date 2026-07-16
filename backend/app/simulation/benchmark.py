from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from hashlib import sha256
from time import perf_counter
from typing import Any

from app.domain import AlphaState
from app.simulation import SimulationEngine, seed_alpha
from app.simulation.diagnostics import (
    correlation_length,
    pattern_census,
    pattern_triggers,
    pattern_triggers_traced,
    scale_free_scan,
)


DEFAULT_BENCHMARK_TICKS = 10_000


def run_benchmark(*, seed: int = 4211, ticks: int = DEFAULT_BENCHMARK_TICKS) -> dict:
    seed_started_at = perf_counter()
    state = seed_alpha(seed=seed)
    seed_duration_ms = _elapsed_ms(seed_started_at)

    advance_started_at = perf_counter()
    SimulationEngine(seed=seed).advance(state, ticks=ticks)
    advance_duration_ms = _elapsed_ms(advance_started_at)

    return _benchmark_report(
        state=state,
        seed=seed,
        ticks=ticks,
        seed_duration_ms=seed_duration_ms,
        advance_duration_ms=advance_duration_ms,
    )


def determinism_signature(state: AlphaState) -> str:
    species_totals: dict[str, int] = defaultdict(int)
    for population in state.populations.values():
        species_totals[population.species_id] += population.population_count

    payload: dict[str, Any] = {
        "universe": {
            "age_years": state.universe.age_years,
            "current_era": state.universe.current_era.value,
            "stability_index": state.universe.stability_index,
            "tick": state.universe.tick,
            "chirality_ee": state.universe.chirality_ee,
            "homochirality_index": state.universe.homochirality_index,
            "chirality_locked": state.universe.chirality_locked,
        },
        "event_counts": _event_counts(state),
        "regions": [
            {
                "id": region.id,
                "collapsed": region.collapsed,
                "dominant_species_id": region.dominant_species_id,
                "energy_level": region.energy_level,
                "resource_density": region.resource_density,
                "stability": region.stability,
                "chirality_ee": region.chirality_ee,
                "chirality_locked": region.chirality_locked,
            }
            for region in sorted(state.regions.values(), key=lambda item: item.id)
        ],
        "species": [
            {
                "id": species.id,
                "generation": species.generation,
                "name": species.name,
                "parent_species_id": species.parent_species_id,
                "population": species_totals.get(species.id, 0),
                "status": species.status.value,
                "chirality": species.chirality,
                "heterochiral_load": species.heterochiral_load,
                "traits": species.traits.to_public(),
            }
            for species in sorted(state.species.values(), key=lambda item: item.id)
        ],
        "populations": [
            {
                "species_id": population.species_id,
                "region_id": population.region_id,
                "population_count": population.population_count,
                "growth_rate": population.growth_rate,
                "migration_pressure": population.migration_pressure,
            }
            for population in sorted(
                state.populations.values(),
                key=lambda item: (item.species_id, item.region_id),
            )
            if population.population_count > 0
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()


def _benchmark_report(
    *,
    state: AlphaState,
    seed: int,
    ticks: int,
    seed_duration_ms: float,
    advance_duration_ms: float,
) -> dict:
    total_duration_ms = round(seed_duration_ms + advance_duration_ms, 3)
    population_count = sum(
        population.population_count for population in state.populations.values()
    )
    collapsed_region_count = sum(
        1 for region in state.regions.values() if region.collapsed
    )
    ticks_per_second = (
        ticks / (advance_duration_ms / 1000)
        if advance_duration_ms > 0
        else 0
    )
    return {
        "seed": seed,
        "ticks": ticks,
        "finalTick": state.universe.tick,
        "finalWorldAge": state.universe.age_years,
        "durationMs": total_duration_ms,
        "seedDurationMs": round(seed_duration_ms, 3),
        "advanceDurationMs": round(advance_duration_ms, 3),
        "ticksPerSecond": round(ticks_per_second, 2),
        "regionCount": len(state.regions),
        "speciesCount": len(state.species),
        "populationCount": population_count,
        "collapsedRegionCount": collapsed_region_count,
        "eventCount": len(state.events),
        "eventCounts": _event_counts(state),
        "topSpecies": _top_species(state, limit=10),
        "determinismSignature": determinism_signature(state),
    }


def _event_counts(state: AlphaState) -> dict[str, int]:
    return dict(sorted(Counter(event.event_type.value for event in state.events).items()))


def _top_species(state: AlphaState, *, limit: int) -> list[dict]:
    species_totals: dict[str, int] = defaultdict(int)
    for population in state.populations.values():
        species_totals[population.species_id] += population.population_count
    ranked = sorted(
        state.species.values(),
        key=lambda species: species_totals.get(species.id, 0),
        reverse=True,
    )
    return [
        {
            "id": species.id,
            "name": species.name,
            "status": species.status.value,
            "population": species_totals.get(species.id, 0),
        }
        for species in ranked[:limit]
    ]


def _elapsed_ms(started_at: float) -> float:
    return (perf_counter() - started_at) * 1000


def _print_human_report(report: dict) -> None:
    print("Evoverse Simulation Benchmark")
    print(f"Seed: {report['seed']}")
    print(f"Ticks: {report['ticks']}")
    print(f"Final Tick: {report['finalTick']}")
    print(f"Final World Age: {report['finalWorldAge']}")
    print(f"Duration: {report['durationMs']} ms")
    print(f"Advance Duration: {report['advanceDurationMs']} ms")
    print(f"Ticks/sec: {report['ticksPerSecond']}")
    print(f"Regions: {report['regionCount']}")
    print(f"Species: {report['speciesCount']}")
    print(f"Population: {report['populationCount']}")
    print(f"Collapsed Regions: {report['collapsedRegionCount']}")
    print(f"Events: {report['eventCount']}")
    print("Event Counts:")
    for event_type, count in report["eventCounts"].items():
        print(f"  {event_type}: {count}")
    print("Top Species:")
    for species in report["topSpecies"]:
        print(
            f"  {species['id']} {species['name']} "
            f"({species['status']}): {species['population']}"
        )
    print(f"Determinism Signature: {report['determinismSignature']}")


def _print_diagnostics(report: dict) -> None:
    if "correlation" in report:
        print("Correlation length (ξ, first zero-crossing of C(r)):")
        for field, result in report["correlation"].items():
            if result["degenerate"]:
                print(f"  {field}: no variance — nothing to correlate")
                continue
            flag = " [floored — read as ≤]" if result["xiFloored"] else ""
            print(f"  {field}: ξ={result['xi']} (c0={result['c0']}){flag}")
    if "scaleFree" in report:
        scan = report["scaleFree"]
        slope = scan["slope"]
        print(
            f"Scale-free scan (field={scan['field']}, seeds={len(scan['seeds'])}): "
            f"verdict={scan['verdict']}"
        )
        if slope["se"] is None:
            # One seed has no error bar, and the slope's seed-to-seed spread swamps
            # the thresholds the verdict uses. Say so where the number is printed.
            print(f"  slope={slope['mean']} — single seed, no error bar; not a verdict")
        else:
            print(
                f"  slope={slope['mean']} ± {slope['se']} (sd={slope['sd']}) "
                f"95% CI [{slope['ci95'][0]}, {slope['ci95'][1]}]"
            )
        print(
            f"  dataCollapseError={scan['dataCollapseError']} "
            f"seedNoise={scan['seedNoise']} ratio={scan['collapseRatio']}"
        )
        for point in scan["points"]:
            spread = f" ± {point['xiSd']}" if point["xiSd"] is not None else ""
            print(
                f"  L={point['L']:>3}  ξ={point['xi']:>6}{spread}  ξ/L={point['xiOverL']}"
                f"  floored={point['flooredSeeds']}/{point['seeds']}"
            )
    if "patterns" in report:
        patterns = report["patterns"]
        morph = patterns["morphotypes"]
        print(
            f"Morphotypes: distinct={morph['distinct']} "
            f"convergenceIndex={morph['convergenceIndex']} "
            f"effectiveCount={morph['effectiveCount']}"
        )
        power = patterns["domainSizePowerLaw"]
        print(
            f"Domain-size power law: τ={power['tau']} R²={power['rSquared']} "
            f"({power['domains']} domains)"
        )
        spatial = patterns["spatialMotifs"]
        print(f"Spatial motifs: distinct={spatial['distinct']}")
        for motif in spatial["top"][:5]:
            print(f"  {motif['key']}: {motif['count']}")
    for key in ("triggers", "triggersTraced"):
        if key in report:
            triggers = report[key]
            print(f"Triggers ({triggers['mode']}):")
            for family, table in triggers["families"].items():
                print(f"  [{family}] {table.get('instances', 0)} instances")
                for row in table["table"][:3]:
                    print(
                        f"    {row['pattern']}  ⇐  {row['condition']}  "
                        f"(lift={row['lift']}, support={row['support']})"
                    )


def _parse_sizes(raw: str) -> list[tuple[int, int]]:
    sizes: list[tuple[int, int]] = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        width, _, height = token.partition("x")
        sizes.append((int(width), int(height)))
    return sizes


DEFAULT_SCALE_FREE_SIZES = "12x9,16x12,20x15,24x18"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Evoverse simulation benchmark.")
    parser.add_argument("--seed", type=int, default=4211)
    parser.add_argument("--ticks", type=int, default=DEFAULT_BENCHMARK_TICKS)
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument(
        "--correlation",
        action="store_true",
        help="Add C(r) and ξ (correlation length) for the final state.",
    )
    parser.add_argument(
        "--patterns",
        action="store_true",
        help="Add the organism pattern census (morphotypes, spatial motifs, ...).",
    )
    parser.add_argument(
        "--triggers",
        action="store_true",
        help="Add the condition→pattern lift table (static co-location).",
    )
    parser.add_argument(
        "--scale-free",
        action="store_true",
        help="Scan ξ across world sizes and report a scale-free verdict.",
    )
    parser.add_argument(
        "--sizes",
        default=DEFAULT_SCALE_FREE_SIZES,
        help=f"Comma-separated WxH sizes for --scale-free (default {DEFAULT_SCALE_FREE_SIZES}).",
    )
    parser.add_argument(
        "--scan-seeds",
        type=int,
        default=1,
        help=(
            "Ensemble size for --scale-free: replay the ladder under this many "
            "consecutive seeds. The default of 1 is fast and exploratory, not a "
            "verdict — the slope moves by ~0.09 between seeds. The worker runs 8."
        ),
    )
    parser.add_argument(
        "--field",
        default="stability",
        help="Field for --scale-free (default stability).",
    )
    parser.add_argument(
        "--trace",
        type=int,
        metavar="STEP",
        help="Trace-mode triggers: emergence conditions sampled every STEP ticks.",
    )
    args = parser.parse_args()

    report = run_benchmark(seed=args.seed, ticks=args.ticks)
    state = seed_alpha(seed=args.seed)
    SimulationEngine(seed=args.seed).advance(state, ticks=args.ticks)
    if args.correlation:
        report["correlation"] = correlation_length(state)
    if args.patterns:
        report["patterns"] = pattern_census(state)
    if args.triggers:
        report["triggers"] = pattern_triggers(state)
    if args.trace is not None:
        report["triggersTraced"] = pattern_triggers_traced(
            args.seed, args.ticks, step=args.trace
        )
    if args.scale_free:
        report["scaleFree"] = scale_free_scan(
            args.seed,
            args.ticks,
            sizes=_parse_sizes(args.sizes),
            field=args.field,
            seeds=args.scan_seeds,
        )

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        _print_human_report(report)
        _print_diagnostics(report)


if __name__ == "__main__":
    main()
