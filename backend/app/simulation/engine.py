from __future__ import annotations

import math
from collections import defaultdict

from app.domain import (
    AlphaState,
    CatalystAction,
    CatalystActionType,
    Era,
    EventType,
    Population,
    Region,
    Species,
    SpeciesStatus,
    Traits,
    clamp,
    clamp_signed,
)
from app.simulation import event_templates
from app.simulation.randomness import stable_rng
from app.simulation.rules import DEFAULT_SIMULATION_RULES, SimulationRules
from app.simulation.seeder import SPECIES_NAMES, _recalculate_universe_chirality


def _hand_word(hand_sign: int) -> str:
    return "right" if hand_sign >= 0 else "left"


# Eras are ordered achievements; the gate only ever moves a universe forward.
_ERA_RANK: dict[Era, int] = {
    Era.GENESIS: 0,
    Era.EXPANSION: 1,
    Era.STABILIZATION: 2,
    Era.INTELLIGENCE: 3,
}


class SimulationEngine:
    """Aggregate population simulation for Phase-1 Alpha."""

    def __init__(
        self,
        seed: int = 4211,
        *,
        rules: SimulationRules | None = None,
    ) -> None:
        self.seed = seed
        self.rules = rules or DEFAULT_SIMULATION_RULES

    def advance(self, state: AlphaState, ticks: int = 1) -> AlphaState:
        for _ in range(ticks):
            state.universe.tick += 1
            state.universe.age_years += 1
            self._advance_regions(state)
            self._advance_chirality(state)
            self._advance_populations(state)
            self._maybe_emit_forced_chronicle_events(state)
            self._maybe_speciate(state)
            self._update_species_statuses(state)
            self._recalculate_dominant_species(state)
            self._update_universe_stability(state)
            self._advance_era(state)
            self._expire_catalyst_actions(state)
        return state

    def register_catalyst_action(
        self,
        state: AlphaState,
        *,
        region_id: str,
        action_type: CatalystActionType,
        user_id: str = "local-catalyst",
    ) -> CatalystAction:
        if region_id not in state.regions:
            raise ValueError(f"Unknown region id: {region_id}")
        action = CatalystAction(
            id=state.next_action_id(),
            universe_id=state.universe.id,
            region_id=region_id,
            action_type=action_type,
            created_at_tick=state.universe.tick,
            expires_at_tick=state.universe.tick + self.rules.catalyst.effect_ticks,
            strength=self.rules.catalyst.strength,
            user_id=user_id,
        )
        state.catalyst_actions.append(action)
        region = state.regions[region_id]
        title, summary = event_templates.catalyst_action(action_type, region)
        state.add_event(
            EventType.CATALYST_ACTION,
            title,
            summary,
            severity=2,
            region_id=region_id,
            payload={
                "action_type": action_type.value,
                "action_id": action.id,
                "user_id": user_id,
            },
        )
        return action

    def _advance_regions(self, state: AlphaState) -> None:
        rules = self.rules.region
        for region in state.regions.values():
            rng = stable_rng(state.seed, "region-drift", state.universe.tick, region.id)
            energy_bias, resource_bias, mutation_bias, catalyst_context = (
                self._active_catalyst_context(state, region.id)
            )
            resource_before = region.resource_density
            energy_delta = (
                rng.uniform(rules.energy_delta_min, rules.energy_delta_max)
                + energy_bias
                + (rules.energy_equilibrium - region.energy_level)
                * rules.energy_reversion_factor
            )
            resource_delta = (
                rng.uniform(rules.resource_delta_min, rules.resource_delta_max)
                + resource_bias
                + (rules.resource_equilibrium - region.resource_density)
                * rules.resource_reversion_factor
            )
            resource_pressure = max(
                -rules.resource_stability_bonus_cap,
                min(
                    rules.resource_stability_bonus_cap,
                    region.resource_density - rules.resource_stability_baseline,
                ),
            )
            stability_delta = (
                rng.uniform(rules.stability_delta_min, rules.stability_delta_max)
                + resource_pressure
                * rules.resource_stability_factor
                + (rules.stability_equilibrium - region.stability)
                * rules.stability_reversion_factor
            )
            if region.collapsed:
                stability_delta -= rules.collapsed_stability_penalty
                energy_delta -= rules.collapsed_energy_penalty

            region.energy_level = round(clamp(region.energy_level + energy_delta), 3)
            region.resource_density = round(clamp(region.resource_density + resource_delta), 3)
            region.stability = round(clamp(region.stability + stability_delta), 3)
            if mutation_bias > 0:
                region.stability = round(
                    clamp(region.stability - mutation_bias * rules.mutation_stability_penalty_factor),
                    3,
                )

            if abs(region.resource_density - resource_before) >= rules.resource_shift_threshold:
                direction = "rise" if region.resource_density > resource_before else "fall"
                title, summary = event_templates.region_resource_shift(region, direction)
                state.add_event(
                    EventType.REGION_RESOURCE_SHIFT,
                    title,
                    summary,
                    severity=2 if direction == "rise" else 3,
                    region_id=region.id,
                    payload={
                        "from": round(resource_before, 3),
                        "to": region.resource_density,
                        "direction": direction,
                        **catalyst_context,
                    },
                )

            if region.collapsed and self._region_has_recovered(region):
                region.collapsed = False
            elif (
                not region.collapsed
                and region.stability < rules.collapse_stability_threshold
                and region.resource_density < rules.collapse_resource_threshold
            ):
                region.collapsed = True
                title, summary = event_templates.region_collapse(region)
                state.add_event(
                    EventType.REGION_COLLAPSE,
                    title,
                    summary,
                    severity=5,
                    region_id=region.id,
                    payload=catalyst_context,
                )

    def _advance_chirality(self, state: AlphaState) -> None:
        """Molecular symmetry breaking (T1). See docs/CHIRALITY_AND_MIND.md §6.1.

        Each unlocked region drifts through a pitchfork bifurcation, then latches
        irreversibly once |ee| crosses the lock threshold. A locked, strongly
        handed region then magnetizes its unlocked neighbours (avalanche), so a
        single broken hand spreads across the map.
        """
        rules = self.rules.chirality
        locked_before = sum(region.chirality_locked for region in state.regions.values())
        newly_locked: list[Region] = []

        for region in state.regions.values():
            if region.chirality_locked:
                continue
            rng = stable_rng(state.seed, "chirality-drift", state.universe.tick, region.id)
            ee = region.chirality_ee
            noise = (rng.random() * 2 - 1) * rules.noise_scale * (1 - abs(ee))
            ee = clamp_signed(ee + rules.amplify_k * ee * (1 - ee * ee) + noise)
            if abs(ee) >= rules.ee_lock_threshold:
                region.chirality_ee = math.copysign(1.0, ee)
                region.chirality_locked = True
                newly_locked.append(region)
            else:
                region.chirality_ee = round(ee, 4)

        coords = {(region.x, region.y): region for region in state.regions.values()}
        deltas: dict[str, float] = defaultdict(float)
        for region in state.regions.values():
            if (
                not region.chirality_locked
                or abs(region.chirality_ee) < rules.avalanche_min_source
            ):
                continue
            push = rules.avalanche_bleed * math.copysign(1.0, region.chirality_ee)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                neighbor = coords.get((region.x + dx, region.y + dy))
                if neighbor is not None and not neighbor.chirality_locked:
                    deltas[neighbor.id] += push
        for region_id, delta in deltas.items():
            region = state.regions[region_id]
            ee = clamp_signed(region.chirality_ee + delta)
            if abs(ee) >= rules.ee_lock_threshold:
                region.chirality_ee = math.copysign(1.0, ee)
                region.chirality_locked = True
                newly_locked.append(region)
            else:
                region.chirality_ee = round(ee, 4)

        # The universe's very first molecular symmetry break is chronicle-worthy.
        if locked_before == 0 and newly_locked:
            first = newly_locked[0]
            hand_sign = 1 if first.chirality_ee > 0 else -1
            title, summary = event_templates.symmetry_break_region(first, hand_sign)
            state.add_event(
                EventType.SYMMETRY_BREAK,
                title,
                summary,
                severity=4,
                region_id=first.id,
                payload={"scope": "region", "hand": _hand_word(hand_sign), "hand_sign": hand_sign},
            )

        self._adopt_species_chirality(state)

        universe_locked_before = state.universe.chirality_locked
        _recalculate_universe_chirality(state)
        if not universe_locked_before and state.universe.chirality_locked:
            title, summary = event_templates.symmetry_break_universe(
                state.universe.homochirality_index
            )
            state.add_event(
                EventType.SYMMETRY_BREAK,
                title,
                summary,
                severity=5,
                payload={
                    "scope": "universe",
                    "homochirality_index": round(state.universe.homochirality_index, 4),
                },
            )

    def _adopt_species_chirality(self, state: AlphaState) -> None:
        """Chiral central dogma (§6.2): an unhanded lineage adopts its origin
        region's hand the first time that region latches. One-way — a lineage that
        has committed a hand never re-derives it here."""
        for species in state.species.values():
            if species.chirality != 0 or species.status == SpeciesStatus.EXTINCT:
                continue
            origin = state.regions.get(species.origin_region_id)
            if origin is None or not origin.chirality_locked:
                continue
            hand_sign = 1 if origin.chirality_ee > 0 else -1
            species.chirality = hand_sign
            title, summary = event_templates.symmetry_break_lineage(species, hand_sign)
            state.add_event(
                EventType.SYMMETRY_BREAK,
                title,
                summary,
                severity=3,
                region_id=origin.id,
                species_id=species.id,
                payload={"scope": "lineage", "hand": _hand_word(hand_sign), "hand_sign": hand_sign},
            )

    def _heterochiral_mismatch(self, species: Species, region: Region) -> float:
        """|ee| only when a *committed* lineage sits in an opposite-hand region;
        0 in a racemic region, a same-hand region, or before the lineage has
        adopted a hand (an unhanded lineage is uncommitted, not wrong-handed).
        See §6.3."""
        region_ee = region.chirality_ee
        if region_ee == 0.0 or species.chirality == 0:
            return 0.0
        region_sign = 1 if region_ee > 0 else -1
        if species.chirality == region_sign:
            return 0.0
        return abs(region_ee)

    def _advance_populations(self, state: AlphaState) -> None:
        rules = self.rules.population
        chirality_rules = self.rules.chirality
        # Population-weighted mismatch per species, resolved into heterochiral_load
        # after the loop so a lineage in many regions gets one honest figure.
        load_weighted: dict[str, float] = defaultdict(float)
        load_total: dict[str, int] = defaultdict(int)
        for population in list(state.populations.values()):
            region = state.regions[population.region_id]
            species = state.species[population.species_id]
            if species.status == SpeciesStatus.EXTINCT:
                continue

            previous_count = population.population_count
            habitat_fit = (
                region.energy_level * species.traits.efficiency
                + region.resource_density * species.traits.adaptation
                + region.stability * species.traits.resilience
            ) / rules.habitat_fit_divisor
            # Heterochiral selection (§6.3): a hand mismatch with the region taxes
            # growth, and a severe one is lethal — scrambled chirality stores no
            # viable information.
            mismatch = self._heterochiral_mismatch(species, region)
            if mismatch > 0:
                habitat_fit *= 1 - chirality_rules.heterochiral_growth_penalty * mismatch
            load_weighted[species.id] += mismatch * previous_count
            load_total[species.id] += previous_count
            density_pressure = min(
                rules.density_pressure_cap,
                previous_count / rules.density_pressure_scale,
            )
            collapse_penalty = rules.collapse_penalty if region.collapsed else 0.0
            growth = (
                (habitat_fit - rules.growth_baseline) * rules.growth_factor
                - density_pressure
                - collapse_penalty
            )
            if mismatch >= chirality_rules.heterochiral_lethal_load:
                growth = min(growth, -chirality_rules.heterochiral_lethal_decline)
            population.growth_rate = round(growth, 4)
            population.migration_pressure = round(
                clamp(
                    (rules.migration_baseline - habitat_fit)
                    + species.traits.mobility * rules.migration_trait_factor
                ),
                3,
            )
            next_count = int(previous_count * (1 + growth))
            population.population_count = max(0, next_count)
            population.last_updated_tick = state.universe.tick

            if (
                previous_count > rules.decline_min_previous_population
                and population.population_count < previous_count * rules.decline_population_ratio
            ):
                decline_percent = int((1 - population.population_count / previous_count) * 100)
                title, summary = event_templates.species_declined(species, decline_percent)
                state.add_event(
                    EventType.SPECIES_DECLINED,
                    title,
                    summary,
                    severity=3 if decline_percent < rules.severe_decline_percent else 4,
                    region_id=region.id,
                    species_id=species.id,
                    payload={"decline_percent": decline_percent},
                )

            if (
                population.population_count > rules.migration_min_population
                and population.migration_pressure > rules.migration_pressure_threshold
            ):
                self._migrate_population(state, population)

        for species_id, total in load_total.items():
            if total > 0:
                state.species[species_id].heterochiral_load = round(
                    load_weighted[species_id] / total, 4
                )

    def _maybe_emit_forced_chronicle_events(self, state: AlphaState) -> None:
        tick = state.universe.tick
        chronicle_rules = self.rules.chronicle
        region_rules = self.rules.region
        if tick % chronicle_rules.forced_resource_shift_interval == 0:
            region = self._select_region(state, "resource-shift", tick)
            previous = region.resource_density
            direction = "rise" if tick % chronicle_rules.forced_resource_rise_interval == 0 else "fall"
            delta = (
                region_rules.forced_resource_rise_delta
                if direction == "rise"
                else region_rules.forced_resource_fall_delta
            )
            region.resource_density = round(clamp(region.resource_density + delta), 3)
            title, summary = event_templates.region_resource_shift(region, direction)
            state.add_event(
                EventType.REGION_RESOURCE_SHIFT,
                title,
                summary,
                severity=2 if direction == "rise" else 3,
                region_id=region.id,
                payload={"from": previous, "to": region.resource_density, "direction": direction},
            )

        if tick % chronicle_rules.forced_decline_interval == 0 and state.species:
            species = self._select_species(state, "decline", tick)
            title, summary = event_templates.species_declined(
                species,
                chronicle_rules.forced_decline_percent,
            )
            state.add_event(
                EventType.SPECIES_DECLINED,
                title,
                summary,
                severity=2,
                region_id=species.origin_region_id,
                species_id=species.id,
                payload={"decline_percent": chronicle_rules.forced_decline_percent},
            )

        if tick % chronicle_rules.forced_collapse_interval == 0:
            region = self._select_region(state, "collapse", tick)
            region.stability = min(region.stability, region_rules.forced_collapse_stability)
            region.resource_density = min(region.resource_density, region_rules.forced_collapse_resource)
            if not region.collapsed:
                region.collapsed = True
                title, summary = event_templates.region_collapse(region)
                state.add_event(
                    EventType.REGION_COLLAPSE,
                    title,
                    summary,
                    severity=5,
                    region_id=region.id,
                )

    def _maybe_speciate(self, state: AlphaState) -> None:
        tick = state.universe.tick
        rules = self.rules.speciation
        mutation_candidates = [
            population
            for population in state.populations.values()
            if population.population_count > rules.candidate_min_population
            and state.species[population.species_id].status != SpeciesStatus.EXTINCT
        ]
        if not mutation_candidates:
            return
        pulse_actions = [
            action
            for action in state.catalyst_actions
            if action.action_type == CatalystActionType.MUTATION_PULSE
        ]
        pulse_regions = {action.region_id for action in pulse_actions}
        should_mutate = tick % rules.interval_ticks == 0 or bool(pulse_regions)
        if not should_mutate:
            return
        rng = stable_rng(state.seed, "speciation", tick, len(state.species))
        population = mutation_candidates[rng.randrange(len(mutation_candidates))]
        if pulse_regions:
            pulse_candidates = [
                item for item in mutation_candidates if item.region_id in pulse_regions
            ]
            if pulse_candidates:
                population = pulse_candidates[rng.randrange(len(pulse_candidates))]

        parent = state.species[population.species_id]
        region = state.regions[population.region_id]
        catalyst_context = (
            self._catalyst_payload_context(
                [action for action in pulse_actions if action.region_id == region.id]
            )
            if pulse_regions
            else {}
        )
        deltas = {
            "efficiency": rng.uniform(rules.efficiency_delta_min, rules.efficiency_delta_max),
            "adaptation": rng.uniform(rules.adaptation_delta_min, rules.adaptation_delta_max),
            "cooperation": rng.uniform(rules.cooperation_delta_min, rules.cooperation_delta_max),
            "mobility": rng.uniform(rules.mobility_delta_min, rules.mobility_delta_max),
            "resilience": rng.uniform(rules.resilience_delta_min, rules.resilience_delta_max),
        }
        # Chiral central dogma (§6.2): the child inherits the parent's hand. A rare
        # flip is almost always lethal — its opposite hand is heterochiral in its
        # (parent-handed) origin region, so selection culls it.
        child_id = state.next_species_id()
        child_chirality = parent.chirality
        chiral_flip = False
        if child_chirality != 0:
            flip_rng = stable_rng(state.seed, "chiral-flip", child_id)
            if flip_rng.random() < self.rules.chirality.inherit_flip_chance:
                child_chirality = -child_chirality
                chiral_flip = True
        child = Species(
            id=child_id,
            universe_id=state.universe.id,
            name=self._next_species_name(state),
            origin_region_id=region.id,
            emerged_at_world_age=state.universe.age_years,
            status=SpeciesStatus.EMERGING,
            generation=parent.generation + 1,
            parent_species_id=parent.id,
            traits=parent.traits.mutated(deltas),
            chirality=child_chirality,
        )
        state.species[child.id] = child
        child_count = max(
            rules.child_min_population,
            int(population.population_count * rules.child_population_fraction),
        )
        population.population_count -= child_count
        state.populations[(child.id, region.id)] = Population(
            species_id=child.id,
            region_id=region.id,
            population_count=child_count,
            energy_consumption=round(
                rules.energy_consumption_base
                + child.traits.efficiency * rules.energy_consumption_efficiency_factor,
                3,
            ),
            growth_rate=0.0,
            migration_pressure=0.0,
            last_updated_tick=state.universe.tick,
        )
        title, summary = event_templates.mutation_detected(parent, region)
        state.add_event(
            EventType.MUTATION_DETECTED,
            title,
            summary,
            severity=3,
            region_id=region.id,
            species_id=parent.id,
            payload={
                "child_species_id": child.id,
                "trait_deltas": {k: round(v, 3) for k, v in deltas.items()},
                **({"chiral_flip": True} if chiral_flip else {}),
                **catalyst_context,
            },
        )
        title, summary = event_templates.species_emerged(child, parent, region)
        state.add_event(
            EventType.SPECIES_EMERGED,
            title,
            summary,
            severity=4,
            region_id=region.id,
            species_id=child.id,
            payload={
                "parent_species_id": parent.id,
                "generation": child.generation,
                **catalyst_context,
            },
        )

    def _migrate_population(self, state: AlphaState, population: Population) -> None:
        rules = self.rules.population
        origin = state.regions[population.region_id]
        neighbors = [
            region
            for region in state.regions.values()
            if abs(region.x - origin.x) + abs(region.y - origin.y) == 1
            and not region.collapsed
        ]
        if not neighbors:
            return
        target = max(neighbors, key=lambda region: region.energy_level + region.resource_density + region.stability)
        moving = int(population.population_count * rules.migration_fraction)
        if moving <= rules.migration_min_moving_population:
            return
        population.population_count -= moving
        key = (population.species_id, target.id)
        if key not in state.populations:
            state.populations[key] = Population(
                species_id=population.species_id,
                region_id=target.id,
                population_count=0,
                energy_consumption=population.energy_consumption,
                growth_rate=0.0,
                migration_pressure=0.0,
                last_updated_tick=state.universe.tick,
            )
        state.populations[key].population_count += moving

    def _update_species_statuses(self, state: AlphaState) -> None:
        rules = self.rules.species_status
        totals = self._species_totals(state)
        if not totals:
            return
        max_total = max(totals.values())
        for species in state.species.values():
            total = totals.get(species.id, 0)
            if total <= rules.extinct_population:
                species.status = SpeciesStatus.EXTINCT
            elif total >= max_total * rules.dominant_share and total > rules.dominant_min_population:
                species.status = SpeciesStatus.DOMINANT
            elif total < rules.declining_population:
                species.status = SpeciesStatus.DECLINING
            elif (
                species.generation > rules.emerging_generation_min
                and state.universe.age_years - species.emerged_at_world_age
                < rules.emerging_age_window
            ):
                species.status = SpeciesStatus.EMERGING
            else:
                species.status = SpeciesStatus.STABLE

    def _recalculate_dominant_species(self, state: AlphaState) -> None:
        by_region: dict[str, list[Population]] = defaultdict(list)
        for population in state.populations.values():
            if population.population_count > 0:
                by_region[population.region_id].append(population)
        for region in state.regions.values():
            populations = by_region.get(region.id, [])
            if not populations:
                region.dominant_species_id = None
                continue
            region.dominant_species_id = max(populations, key=lambda item: item.population_count).species_id

    def _update_universe_stability(self, state: AlphaState) -> None:
        if not state.regions:
            state.universe.stability_index = 0.0
            return
        stability = sum(region.stability for region in state.regions.values()) / len(state.regions)
        collapse_ratio = sum(1 for region in state.regions.values() if region.collapsed) / len(state.regions)
        state.universe.stability_index = round(
            clamp(
                stability
                - collapse_ratio * self.rules.universe.collapse_ratio_stability_penalty
            ),
            3,
        )

    def _advance_era(self, state: AlphaState) -> None:
        """Two-tier maturity gate (§6.4). Eras are earned, never seeded or lost:

        * Genesis/Expansion → **Stabilization** once the universe's homochirality
          index crosses ``life_gate_index`` (T1: chemistry becomes life).
        * Stabilization → **Intelligence** once homochirality crosses
          ``mind_gate_index`` *and* some lineage has ``mind_locked`` (T2). Because
          no lineage locks a mind until the cognitive tier ships, Intelligence
          stays unreachable here — earned, not given.
        """
        rules = self.rules.chirality
        idx = state.universe.homochirality_index
        current = state.universe.current_era
        target = current

        if _ERA_RANK[current] < _ERA_RANK[Era.STABILIZATION] and idx >= rules.life_gate_index:
            target = Era.STABILIZATION
        if (
            _ERA_RANK[target] < _ERA_RANK[Era.INTELLIGENCE]
            and idx >= rules.mind_gate_index
            and any(species.mind_locked for species in state.species.values())
        ):
            target = Era.INTELLIGENCE

        if _ERA_RANK[target] > _ERA_RANK[current]:
            state.universe.current_era = target
            title, summary = event_templates.era_advanced(current, target, idx)
            state.add_event(
                EventType.ERA_ADVANCED,
                title,
                summary,
                severity=5,
                payload={
                    "from_era": current.value,
                    "to_era": target.value,
                    "homochirality_index": round(idx, 4),
                },
            )

    def _expire_catalyst_actions(self, state: AlphaState) -> None:
        state.catalyst_actions = [
            action for action in state.catalyst_actions if action.expires_at_tick > state.universe.tick
        ]

    def _active_catalyst_context(
        self,
        state: AlphaState,
        region_id: str,
    ) -> tuple[float, float, float, dict]:
        energy_bias = 0.0
        resource_bias = 0.0
        mutation_bias = 0.0
        active_actions: list[CatalystAction] = []
        for action in state.catalyst_actions:
            if action.region_id != region_id:
                continue
            active_actions.append(action)
            if action.action_type == CatalystActionType.ENERGY_PULSE:
                energy_bias += action.strength
            elif action.action_type == CatalystActionType.RESOURCE_BURST:
                resource_bias += action.strength
            elif action.action_type == CatalystActionType.MUTATION_PULSE:
                mutation_bias += action.strength
        return (
            energy_bias,
            resource_bias,
            mutation_bias,
            self._catalyst_payload_context(active_actions),
        )

    def _catalyst_payload_context(self, actions: list[CatalystAction]) -> dict:
        if not actions:
            return {}
        return {
            "catalyst_action_ids": [action.id for action in actions],
            "catalyst_user_ids": sorted({action.user_id for action in actions}),
            "catalyst_action_types": sorted({action.action_type.value for action in actions}),
        }

    def _region_has_recovered(self, region: Region) -> bool:
        rules = self.rules.region
        return (
            region.stability >= rules.recovery_stability_threshold
            and region.resource_density >= rules.recovery_resource_threshold
            and region.energy_level >= rules.recovery_energy_threshold
        )

    def _species_totals(self, state: AlphaState) -> dict[str, int]:
        totals: dict[str, int] = defaultdict(int)
        for population in state.populations.values():
            totals[population.species_id] += population.population_count
        return dict(totals)

    def _select_region(self, state: AlphaState, scope: str, tick: int) -> Region:
        region_ids = sorted(state.regions)
        rng = stable_rng(state.seed, scope, tick)
        return state.regions[region_ids[rng.randrange(len(region_ids))]]

    def _select_species(self, state: AlphaState, scope: str, tick: int) -> Species:
        species_ids = sorted(state.species)
        rng = stable_rng(state.seed, scope, tick)
        return state.species[species_ids[rng.randrange(len(species_ids))]]

    def _next_species_name(self, state: AlphaState) -> str:
        index = len(state.species)
        if index < len(SPECIES_NAMES):
            return SPECIES_NAMES[index]
        prefix = SPECIES_NAMES[index % len(SPECIES_NAMES)]
        return f"{prefix}-{index + 1}"
