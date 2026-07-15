"""Read-only, deterministic diagnostics over an ``AlphaState``.

Implements the design in ``docs/CORRELATION_AND_PATTERNS.md``:

* **Part A** — a scale-free correlation length ``ξ`` over region fluctuations, the
  starling-flock diagnostic (Cavagna–Giardina–Parisi): subtract the mean, measure how
  far residual fluctuations stay correlated, and check whether ``ξ`` scales with world
  size.
* **Part B** — an organism *pattern census*: capture → canonicalise → count recurring
  motifs (morphotypes, spatial tilings, domain sizes, lineage/event motifs).
* **Part C** — *which conditions trigger which patterns*: a lift table joining each
  motif to the state it forms under.

Everything here is a pure fold over the state (no new randomness): the same
``(seed, ticks, size)`` always yields identical numbers. Iteration is in sorted id
order so counters and curves are order-independent.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict, deque
from typing import Any

from app.domain import AlphaState, Region

# --- Part A -----------------------------------------------------------------

DEFAULT_FIELDS: tuple[str, ...] = (
    "stability",
    "energy_level",
    "resource_density",
    "growth_rate",
)


def _region_field_value(state: AlphaState, region: Region, field: str) -> float:
    """The scalar φ used to build the fluctuation field δφ for one region.

    ``growth_rate`` is aggregated as the mean over the region's live populations —
    the closest analogue to a starling's *velocity* (a rate of change). The other
    fields read straight off the region.
    """
    if field == "growth_rate":
        rates = [
            population.growth_rate
            for population in state.populations.values()
            if population.region_id == region.id and population.population_count > 0
        ]
        return sum(rates) / len(rates) if rates else 0.0
    return float(getattr(region, field))


def _distance(a: Region, b: Region, metric: str) -> int:
    if metric == "euclidean":
        return int(round(math.hypot(a.x - b.x, a.y - b.y)))
    return abs(a.x - b.x) + abs(a.y - b.y)  # manhattan (matches 4-neighbour coupling)


def correlation_field(
    state: AlphaState,
    field: str,
    *,
    metric: str = "manhattan",
) -> dict[str, Any]:
    """C(r) and ξ for one scalar field, over non-collapsed regions.

    δφ(i) = φ(i) − mean(φ); C(r) is the mean of δφ(i)·δφ(j) over region pairs at
    distance r, normalised so C(0) = 1. ξ is the first zero-crossing of C(r) (which
    ``∑ δφ = 0`` guarantees exists), linearly interpolated. If C(r) never crosses,
    the field is saturated/ordered and ξ is reported as the max distance with
    ``saturated: True``.
    """
    regions = sorted(
        (region for region in state.regions.values() if not region.collapsed),
        key=lambda region: region.id,
    )
    n = len(regions)
    if n < 2:
        return {"xi": 0.0, "c0": 0.0, "curve": [], "saturated": False, "sampleSize": n}

    values = [_region_field_value(state, region, field) for region in regions]
    mean = sum(values) / n
    deltas = [value - mean for value in values]
    c0 = sum(delta * delta for delta in deltas) / n
    if c0 == 0:
        return {"xi": 0.0, "c0": 0.0, "curve": [], "saturated": True, "sampleSize": n}

    pair_sum: dict[int, float] = defaultdict(float)
    pair_count: dict[int, int] = defaultdict(int)
    for i in range(n):
        for j in range(i + 1, n):
            r = _distance(regions[i], regions[j], metric)
            pair_sum[r] += deltas[i] * deltas[j]
            pair_count[r] += 1

    curve = [
        (r, (pair_sum[r] / pair_count[r]) / c0)
        for r in sorted(pair_sum)
        if pair_count[r] > 0
    ]
    xi, saturated = _first_zero_crossing(curve)
    return {
        "xi": round(xi, 4),
        "c0": round(c0, 6),
        "curve": [[r, round(c, 4)] for r, c in curve],
        "saturated": saturated,
        "sampleSize": n,
    }


def _first_zero_crossing(curve: list[tuple[int, float]]) -> tuple[float, bool]:
    """Return (ξ, saturated). ξ = first r where C(r) crosses below zero."""
    if not curve:
        return 0.0, False
    prev_r, prev_c = curve[0]
    if prev_c < 0:
        return float(prev_r), False
    for r, c in curve[1:]:
        if c < 0 <= prev_c:
            span = prev_c - c
            frac = prev_c / span if span else 0.0
            return prev_r + (r - prev_r) * frac, False
        prev_r, prev_c = r, c
    return float(curve[-1][0]), True  # never crossed → ordered/saturated


def correlation_length(
    state: AlphaState,
    *,
    fields: tuple[str, ...] = DEFAULT_FIELDS,
    metric: str = "manhattan",
) -> dict[str, Any]:
    """ξ and C(r) for every field in ``fields``."""
    return {field: correlation_field(state, field, metric=metric) for field in fields}


def scale_free_scan(
    seed: int,
    ticks: int,
    *,
    sizes: list[tuple[int, int]],
    field: str = "stability",
    metric: str = "manhattan",
) -> dict[str, Any]:
    """Re-seed & advance at each (width, height); measure how ξ scales with L.

    Scale-free / critical ⇒ ξ grows with L (ξ/L roughly constant) and the C(r/L)
    curves collapse onto one another. Deterministic: only width/height vary, the seed
    is held fixed.
    """
    # Imported here to avoid any import-time coupling; safe (not in the package init).
    from app.simulation import SimulationEngine, seed_alpha

    points: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    normalized_curves: list[list[tuple[float, float]]] = []
    for width, height in sizes:
        # The seeder pins species origins to fixed region ids (up to region-101), so
        # worlds smaller than the default 12x9 can't be seeded. Skip rather than crash;
        # the scale-free ladder scans upward from the default.
        try:
            state = seed_alpha(seed=seed, width=width, height=height)
        except KeyError:
            skipped.append({"width": width, "height": height, "reason": "unseedable-size"})
            continue
        SimulationEngine(seed=seed).advance(state, ticks=ticks)
        result = correlation_field(state, field, metric=metric)
        length = max(width, height)
        xi = result["xi"]
        points.append(
            {
                "width": width,
                "height": height,
                "L": length,
                "xi": xi,
                "xiOverL": round(xi / length, 4) if length else 0.0,
                "saturated": result["saturated"],
            }
        )
        if result["curve"]:
            normalized_curves.append(
                [(r / length, c) for r, c in result["curve"]]
            )

    collapse_error = _data_collapse_error(normalized_curves)
    return {
        "field": field,
        "metric": metric,
        "ticks": ticks,
        "points": points,
        "skipped": skipped,
        "dataCollapseError": collapse_error,
        "verdict": _scale_free_verdict(points, collapse_error),
    }


def _data_collapse_error(curves: list[list[tuple[float, float]]]) -> float | None:
    """RMS spread of the C(r/L) curves resampled on a common x = r/L grid.

    Low spread ⇒ the curves collapse ⇒ scale-free. ``None`` if too few curves.
    """
    if len(curves) < 2:
        return None
    grid = [x / 10 for x in range(1, 11)]  # 0.1 .. 1.0
    spreads: list[float] = []
    for x in grid:
        samples = [_interp(curve, x) for curve in curves]
        samples = [s for s in samples if s is not None]
        if len(samples) < 2:
            continue
        mean = sum(samples) / len(samples)
        variance = sum((s - mean) ** 2 for s in samples) / len(samples)
        spreads.append(variance)
    if not spreads:
        return None
    return round(math.sqrt(sum(spreads) / len(spreads)), 4)


def _interp(curve: list[tuple[float, float]], x: float) -> float | None:
    """Linear interpolation of a monotonic-x curve at x; None if out of range."""
    if not curve or x < curve[0][0] or x > curve[-1][0]:
        return None
    prev_x, prev_y = curve[0]
    for cx, cy in curve[1:]:
        if cx >= x:
            span = cx - prev_x
            frac = (x - prev_x) / span if span else 0.0
            return prev_y + (cy - prev_y) * frac
        prev_x, prev_y = cx, cy
    return curve[-1][1]


def _scale_free_verdict(points: list[dict[str, Any]], collapse_error: float | None) -> str:
    """Heuristic label from how ξ tracks L. Numbers travel with it — judge, don't trust."""
    usable = [p for p in points if not p["saturated"]]
    if len(points) >= 2 and len(usable) <= len(points) // 2:
        return "super_critical"  # most sizes never cross zero → one ordered domain
    if len(points) < 2:
        return "insufficient"
    ls = [p["L"] for p in points]
    xis = [p["xi"] for p in points]
    slope = _least_squares_slope(ls, xis)
    if slope >= 0.25 and (collapse_error is None or collapse_error <= 0.05):
        return "critical"  # ξ grows with L and curves collapse → scale-free
    if slope < 0.08:
        return "sub_critical"  # ξ ~ constant while L grows → fixed patch size
    return "intermediate"


def _least_squares_slope(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    denom = sum((x - mean_x) ** 2 for x in xs)
    if denom == 0:
        return 0.0
    return sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / denom


# --- Part B -----------------------------------------------------------------

MORPHOTYPE_BINS = 1  # decimal places for trait quantisation (0.1 buckets)
EVENT_NGRAM_N = 3
DEFAULT_TOP = 10

_TRAIT_KEYS = ("efficiency", "adaptation", "cooperation", "mobility", "resilience")


def _entropy(counts: list[int]) -> float:
    """Shannon entropy (bits) of a multiset of counts."""
    total = sum(counts)
    if total <= 0:
        return 0.0
    entropy = 0.0
    for count in counts:
        if count <= 0:
            continue
        p = count / total
        entropy -= p * math.log2(p)
    return entropy


def _diversity(counter: Counter) -> dict[str, Any]:
    counts = list(counter.values())
    entropy = _entropy(counts)
    return {
        "distinct": len(counter),
        "entropy": round(entropy, 4),
        "effectiveCount": round(2**entropy, 4),
    }


def _species_totals(state: AlphaState) -> dict[str, int]:
    totals: dict[str, int] = defaultdict(int)
    for population in state.populations.values():
        totals[population.species_id] += population.population_count
    return totals


def _lineage_root(state: AlphaState, species_id: str, cache: dict[str, str]) -> str:
    if species_id in cache:
        return cache[species_id]
    chain: list[str] = []
    current: str | None = species_id
    seen: set[str] = set()
    while current is not None and current in state.species and current not in seen:
        seen.add(current)
        chain.append(current)
        parent = state.species[current].parent_species_id
        if parent is None or parent not in state.species:
            break
        current = parent
    root = chain[-1] if chain else species_id
    for member in chain:
        cache[member] = root
    return root


def _morphotype_signature(species: Any) -> tuple[float, ...]:
    public = species.traits.to_public()
    return tuple(round(public[key], MORPHOTYPE_BINS) for key in _TRAIT_KEYS)


def _morphotype_census(state: AlphaState) -> dict[str, Any]:
    totals = _species_totals(state)
    root_cache: dict[str, str] = {}
    by_sig_species: dict[tuple, list[str]] = defaultdict(list)
    by_sig_lineages: dict[tuple, set[str]] = defaultdict(set)
    by_sig_population: dict[tuple, int] = defaultdict(int)
    for species in sorted(state.species.values(), key=lambda item: item.id):
        sig = _morphotype_signature(species)
        by_sig_species[sig].append(species.id)
        by_sig_lineages[sig].add(_lineage_root(state, species.id, root_cache))
        by_sig_population[sig] += totals.get(species.id, 0)

    counter = Counter({sig: len(members) for sig, members in by_sig_species.items()})
    convergent = sum(1 for sig in by_sig_lineages if len(by_sig_lineages[sig]) >= 2)
    top = [
        {
            "sig": list(sig),
            "species": len(by_sig_species[sig]),
            "lineages": len(by_sig_lineages[sig]),
            "population": by_sig_population[sig],
        }
        for sig, _ in sorted(
            counter.items(), key=lambda item: (-item[1], item[0])
        )[:DEFAULT_TOP]
    ]
    return {
        **_diversity(counter),
        "convergenceIndex": round(convergent / len(counter), 4) if counter else 0.0,
        "top": top,
    }


def _region_coords(state: AlphaState) -> dict[tuple[int, int], Region]:
    return {(region.x, region.y): region for region in state.regions.values()}


_NEIGHBOUR_OFFSETS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def _spatial_motif_key(region: Region, coords: dict[tuple[int, int], Region]) -> str | None:
    """Canonical, identity-invariant local tiling motif around ``region``.

    Center label = 0; neighbours relabelled by frequency then id; empty/no-dominant
    neighbour = -1. Returns ``None`` for regions with no dominant species.
    """
    center = region.dominant_species_id
    if center is None:
        return None
    neighbour_ids: list[str | None] = []
    for dx, dy in _NEIGHBOUR_OFFSETS:
        neighbour = coords.get((region.x + dx, region.y + dy))
        if neighbour is None:
            continue  # off-grid edge — fewer neighbours encodes the boundary
        neighbour_ids.append(neighbour.dominant_species_id)

    non_center = Counter(nid for nid in neighbour_ids if nid is not None and nid != center)
    ordered = [nid for nid, _ in sorted(non_center.items(), key=lambda item: (-item[1], item[0]))]
    label_of = {nid: index + 1 for index, nid in enumerate(ordered)}
    labels: list[int] = []
    for nid in neighbour_ids:
        if nid is None:
            labels.append(-1)
        elif nid == center:
            labels.append(0)
        else:
            labels.append(label_of[nid])
    return "0|" + ",".join(str(label) for label in sorted(labels))


def _spatial_motif_census(state: AlphaState) -> dict[str, Any]:
    coords = _region_coords(state)
    counter: Counter = Counter()
    for region in sorted(state.regions.values(), key=lambda item: item.id):
        key = _spatial_motif_key(region, coords)
        if key is not None:
            counter[key] += 1
    top = [
        {"key": key, "count": count}
        for key, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))[:DEFAULT_TOP]
    ]
    return {**_diversity(counter), "top": top}


def _domain_sizes(state: AlphaState) -> list[int]:
    """Flood-fill connected regions sharing the same dominant species into domains."""
    coords = _region_coords(state)
    visited: set[tuple[int, int]] = set()
    sizes: list[int] = []
    for start in sorted(coords):
        if start in visited:
            continue
        region = coords[start]
        species_id = region.dominant_species_id
        if species_id is None:
            visited.add(start)
            continue
        size = 0
        queue: deque[tuple[int, int]] = deque([start])
        visited.add(start)
        while queue:
            cx, cy = queue.popleft()
            size += 1
            for dx, dy in _NEIGHBOUR_OFFSETS:
                nxt = (cx + dx, cy + dy)
                neighbour = coords.get(nxt)
                if (
                    neighbour is not None
                    and nxt not in visited
                    and neighbour.dominant_species_id == species_id
                ):
                    visited.add(nxt)
                    queue.append(nxt)
        sizes.append(size)
    return sizes


def _domain_size_powerlaw(state: AlphaState) -> dict[str, Any]:
    """Fit P(s) ∝ s^(−τ) on the domain-size histogram (log-log least squares).

    A power law here is the pattern-level signature of the same criticality ξ ∝ L
    measures at the field level.
    """
    sizes = _domain_sizes(state)
    histogram = Counter(sizes)
    points = [
        (math.log(size), math.log(count))
        for size, count in sorted(histogram.items())
        if size > 0 and count > 0
    ]
    result: dict[str, Any] = {
        "domains": len(sizes),
        "distinctSizes": len(histogram),
        "histogram": [[size, histogram[size]] for size in sorted(histogram)],
    }
    if len(points) >= 2:
        xs = [x for x, _ in points]
        ys = [y for _, y in points]
        slope = _least_squares_slope(xs, ys)
        result["tau"] = round(-slope, 4)
        result["rSquared"] = round(_r_squared(xs, ys, slope), 4)
    else:
        result["tau"] = None
        result["rSquared"] = None
    return result


def _r_squared(xs: list[float], ys: list[float], slope: float) -> float:
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    intercept = mean_y - slope * mean_x
    ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys))
    ss_tot = sum((y - mean_y) ** 2 for y in ys)
    if ss_tot == 0:
        return 1.0
    return 1 - ss_res / ss_tot


def _lineage_motif_census(state: AlphaState) -> dict[str, Any]:
    children: dict[str, list[str]] = defaultdict(list)
    for species in sorted(state.species.values(), key=lambda item: item.id):
        if species.parent_species_id is not None:
            children[species.parent_species_id].append(species.id)
    counter: Counter = Counter()
    for species in sorted(state.species.values(), key=lambda item: item.id):
        kids = children.get(species.id, [])
        extinct = sum(
            1
            for kid in kids
            if state.species[kid].status.value == "extinct"
        )
        counter[(len(kids), extinct)] += 1
    top = [
        {"children": key[0], "extinctChildren": key[1], "count": count}
        for key, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))[:DEFAULT_TOP]
    ]
    return {**_diversity(counter), "top": top}


def _event_ngram_census(state: AlphaState, *, n: int = EVENT_NGRAM_N) -> dict[str, Any]:
    by_species: dict[str, list[tuple[int, str, str]]] = defaultdict(list)
    for event in state.events:
        if event.species_id is not None:
            by_species[event.species_id].append(
                (event.tick, event.id, event.event_type.value)
            )
    counter: Counter = Counter()
    for species_id in sorted(by_species):
        sequence = [item[2] for item in sorted(by_species[species_id])]
        for start in range(len(sequence) - n + 1):
            counter[tuple(sequence[start : start + n])] += 1
    top = [
        {"ngram": ">".join(key), "count": count}
        for key, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))[:DEFAULT_TOP]
    ]
    return {**_diversity(counter), "n": n, "top": top}


def pattern_census(state: AlphaState) -> dict[str, Any]:
    """Capture and count recurring organism motifs across four levels."""
    return {
        "morphotypes": _morphotype_census(state),
        "spatialMotifs": _spatial_motif_census(state),
        "domainSizePowerLaw": _domain_size_powerlaw(state),
        "lineageMotifs": _lineage_motif_census(state),
        "eventNgrams": _event_ngram_census(state),
    }


# --- Part C -----------------------------------------------------------------

_LOW = 0.34
_HIGH = 0.67


def _band(value: float) -> str:
    if value < _LOW:
        return "low"
    if value < _HIGH:
        return "mid"
    return "high"


def _active_catalyst_types(state: AlphaState, region_id: str) -> str:
    types = sorted(
        {
            action.action_type.value
            for action in state.catalyst_actions
            if action.region_id == region_id
        }
    )
    return "+".join(types) if types else "none"


def condition_vector(state: AlphaState, region: Region) -> str:
    """A readable, quantised snapshot of the state a pattern instance sits in."""
    coords = _region_coords(state)
    neighbour_collapsed = sum(
        1
        for dx, dy in _NEIGHBOUR_OFFSETS
        if (n := coords.get((region.x + dx, region.y + dy))) is not None and n.collapsed
    )
    sign = 0 if region.chirality_ee == 0 else (1 if region.chirality_ee > 0 else -1)
    return "|".join(
        [
            f"era={state.universe.current_era.name}",
            f"stab={_band(region.stability)}",
            f"res={_band(region.resource_density)}",
            f"energy={_band(region.energy_level)}",
            f"collapsed={int(region.collapsed)}",
            f"ncollapsed={neighbour_collapsed}",
            f"chir={sign}{'L' if region.chirality_locked else ''}",
            f"cat={_active_catalyst_types(state, region.id)}",
        ]
    )


def _lift_table(instances: list[tuple[str, str]], *, top: int = 20) -> dict[str, Any]:
    """Build the (pattern, condition) → lift table from co-occurrence instances."""
    n = len(instances)
    if n == 0:
        return {"table": [], "conditionProfiles": {}, "topByCondition": {}}
    count_m: Counter = Counter(m for m, _ in instances)
    count_c: Counter = Counter(c for _, c in instances)
    count_mc: Counter = Counter(instances)

    table = []
    for (motif, condition), support in count_mc.items():
        p_given_c = support / count_c[condition]
        p_m = count_m[motif] / n
        lift = p_given_c / p_m if p_m else 0.0
        table.append(
            {
                "pattern": motif,
                "condition": condition,
                "lift": round(lift, 4),
                "support": support,
                "pGivenC": round(p_given_c, 4),
            }
        )
    table.sort(key=lambda row: (-(row["lift"] * math.log(row["support"] + 1)), row["pattern"]))

    profiles: dict[str, str] = {}
    for motif, _ in count_m.most_common(DEFAULT_TOP):
        best = max(
            (row for row in table if row["pattern"] == motif),
            key=lambda row: (row["support"], row["lift"]),
            default=None,
        )
        if best is not None:
            profiles[motif] = best["condition"]

    top_by_condition: dict[str, list[dict[str, Any]]] = {}
    for condition, _ in count_c.most_common(DEFAULT_TOP):
        rows = sorted(
            (row for row in table if row["condition"] == condition),
            key=lambda row: (-row["support"], -row["lift"]),
        )[:3]
        top_by_condition[condition] = [
            {"pattern": row["pattern"], "lift": row["lift"], "support": row["support"]}
            for row in rows
        ]

    return {
        "instances": n,
        "table": table[:top],
        "conditionProfiles": profiles,
        "topByCondition": top_by_condition,
    }


def pattern_triggers(state: AlphaState) -> dict[str, Any]:
    """Static co-location: which conditions each spatial motif forms under."""
    coords = _region_coords(state)
    instances: list[tuple[str, str]] = []
    for region in sorted(state.regions.values(), key=lambda item: item.id):
        motif = _spatial_motif_key(region, coords)
        if motif is None:
            continue
        instances.append((f"spatial:{motif}", condition_vector(state, region)))
    return {"mode": "static", **_lift_table(instances)}


def _global_condition(state: AlphaState) -> str:
    regions = [region for region in state.regions.values() if not region.collapsed]
    if regions:
        mean_stab = sum(r.stability for r in regions) / len(regions)
        mean_res = sum(r.resource_density for r in regions) / len(regions)
    else:
        mean_stab = mean_res = 0.0
    catalysts = sorted({action.action_type.value for action in state.catalyst_actions})
    collapsed = sum(1 for region in state.regions.values() if region.collapsed)
    return "|".join(
        [
            f"era={state.universe.current_era.name}",
            f"stab={_band(mean_stab)}",
            f"res={_band(mean_res)}",
            f"homochir={_band(state.universe.homochirality_index)}",
            f"collapsed={collapsed}",
            f"cat={'+'.join(catalysts) if catalysts else 'none'}",
        ]
    )


def pattern_triggers_traced(
    seed: int,
    ticks: int,
    *,
    step: int = 200,
) -> dict[str, Any]:
    """Trace mode: stamp each motif with the global condition it *first appears* under.

    Deterministic replay — advances in ``step``-tick samples and records, for every
    spatial motif not seen before, the current global condition (its emergence
    conditions). The engine is never modified; we re-derive by replay.
    """
    from app.simulation import SimulationEngine, seed_alpha

    state = seed_alpha(seed=seed)
    engine = SimulationEngine(seed=seed)
    seen: set[str] = set()
    instances: list[tuple[str, str]] = []

    def sample() -> None:
        coords = _region_coords(state)
        condition = _global_condition(state)
        present = {
            key
            for region in state.regions.values()
            if (key := _spatial_motif_key(region, coords)) is not None
        }
        for motif in sorted(present - seen):
            instances.append((f"spatial:{motif}", condition))
            seen.add(motif)

    sample()
    remaining = ticks
    while remaining > 0:
        advance_by = min(step, remaining)
        engine.advance(state, ticks=advance_by)
        remaining -= advance_by
        sample()

    return {"mode": "traced", "step": step, "ticks": ticks, **_lift_table(instances)}
