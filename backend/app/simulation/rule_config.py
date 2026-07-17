from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, fields
from hashlib import sha256
from typing import Any

from app.domain import CatalystActionType
from app.simulation.rules import (
    CatalystRules,
    ChiralityRules,
    ChronicleRules,
    DEFAULT_SIMULATION_RULES,
    PopulationRules,
    RegionRules,
    SimulationRules,
    SpeciationRules,
    SpeciesStatusRules,
    UniverseRules,
)


RULE_MODEL = "simulation_rules_v1"

SECTION_TYPES = {
    "catalyst": CatalystRules,
    "region": RegionRules,
    "population": PopulationRules,
    "speciation": SpeciationRules,
    "chronicle": ChronicleRules,
    "species_status": SpeciesStatusRules,
    "universe": UniverseRules,
    "chirality": ChiralityRules,
}


def _public_key(key: Any) -> str:
    if isinstance(key, CatalystActionType):
        return key.value
    key_text = str(key)
    if "_" not in key_text:
        return key_text
    head, *tail = key_text.split("_")
    return head + "".join(part.capitalize() for part in tail)


PUBLIC_SECTION_KEYS = {
    _public_key(section): section for section in SECTION_TYPES
}


@dataclass(frozen=True)
class RuleValidationResult:
    valid: bool
    rules: SimulationRules
    public_rules: dict[str, Any]
    rules_hash: str
    errors: list[dict[str, str]]
    warnings: list[dict[str, str]]


def rules_to_public(rules: SimulationRules = DEFAULT_SIMULATION_RULES) -> dict[str, Any]:
    return _public_value(asdict(rules))


def rules_hash(rules: SimulationRules) -> str:
    encoded = json.dumps(
        rules_to_public(rules),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def validate_rules_update(
    update: dict[str, Any],
    current: SimulationRules = DEFAULT_SIMULATION_RULES,
) -> RuleValidationResult:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    current_public = rules_to_public(current)
    if not isinstance(update, dict):
        errors.append(_error("rules", "Rules payload must be an object."))
        return _result(current, errors, warnings)

    merged = json.loads(json.dumps(current_public))
    for public_section, section_update in update.items():
        private_section = PUBLIC_SECTION_KEYS.get(public_section)
        if private_section is None:
            errors.append(_error(public_section, "Unknown rules section."))
            continue
        if not isinstance(section_update, dict):
            errors.append(_error(public_section, "Rules section must be an object."))
            continue
        _merge_section(
            merged[public_section],
            section_update,
            section_path=public_section,
            section_type=SECTION_TYPES[private_section],
            errors=errors,
        )

    build_errors: list[dict[str, str]] = []
    candidate = _rules_from_public(merged, build_errors)
    errors.extend(build_errors)
    if candidate is not None:
        _validate_semantics(candidate, errors, warnings)
    if errors or candidate is None:
        return _result(current, errors, warnings)
    return _result(candidate, errors, warnings)


def rules_from_public(public_rules: dict[str, Any]) -> SimulationRules:
    errors: list[dict[str, str]] = []
    rules = _rules_from_public(public_rules, errors)
    if errors or rules is None:
        messages = "; ".join(f"{item['path']}: {item['message']}" for item in errors)
        raise ValueError(messages or "Invalid simulation rules.")
    semantic_errors: list[dict[str, str]] = []
    _validate_semantics(rules, semantic_errors, [])
    if semantic_errors:
        messages = "; ".join(
            f"{item['path']}: {item['message']}" for item in semantic_errors
        )
        raise ValueError(messages)
    return rules


def reload_strategy(*, runtime_applied: bool) -> dict[str, Any]:
    return {
        "api": {
            "mode": "hot_reload",
            "status": "reloaded" if runtime_applied else "not_applied",
        },
        "worker": {
            "mode": "repository_reload_before_next_step",
            "status": "pending_next_step" if runtime_applied else "not_applied",
        },
        "restartRequired": False,
    }


def _merge_section(
    target: dict[str, Any],
    update: dict[str, Any],
    *,
    section_path: str,
    section_type: type,
    errors: list[dict[str, str]],
) -> None:
    field_names = {field.name for field in fields(section_type)}
    public_field_names = {_public_key(field_name): field_name for field_name in field_names}
    for public_key, value in update.items():
        private_key = public_field_names.get(public_key)
        path = f"{section_path}.{public_key}"
        if private_key is None:
            errors.append(_error(path, "Unknown rule key."))
            continue
        if public_key == "dailyLimits":
            if not isinstance(value, dict):
                errors.append(_error(path, "Daily limits must be an object."))
                continue
            current_limits = target.get(public_key, {})
            for action_key, limit in value.items():
                action_path = f"{path}.{action_key}"
                if action_key not in {item.value for item in CatalystActionType}:
                    errors.append(_error(action_path, "Unknown catalyst action type."))
                    continue
                if not _is_int(limit) or int(limit) < 0:
                    errors.append(_error(action_path, "Daily limit must be a non-negative integer."))
                    continue
                current_limits[action_key] = int(limit)
            target[public_key] = current_limits
            continue
        target[public_key] = value


def _rules_from_public(
    public_rules: dict[str, Any],
    errors: list[dict[str, str]],
) -> SimulationRules | None:
    kwargs: dict[str, Any] = {}
    for private_section, section_type in SECTION_TYPES.items():
        section_errors: list[dict[str, str]] = []
        public_section = _public_key(private_section)
        section_payload = public_rules.get(public_section)
        if section_payload is None:
            # A stored config predating this section (e.g. "chirality" added in a
            # later migration) falls back to the section default rather than
            # failing to load. Keeps old revisions restorable.
            kwargs[private_section] = section_type()
            continue
        if not isinstance(section_payload, dict):
            section_errors.append(_error(public_section, "Rules section is missing or invalid."))
            errors.extend(section_errors)
            continue
        section_kwargs: dict[str, Any] = {}
        for field in fields(section_type):
            public_field = _public_key(field.name)
            path = f"{public_section}.{public_field}"
            if public_field not in section_payload:
                # A stored config predating this field (e.g. the heterochiral knobs
                # added after the T1 chirality slice) falls back to the field
                # default rather than failing to load. The update path always merges
                # onto full defaults, so only stored configs reach this branch.
                section_kwargs[field.name] = getattr(section_type(), field.name)
                continue
            value = section_payload[public_field]
            if field.name == "daily_limits":
                section_kwargs[field.name] = _daily_limits_from_public(
                    value,
                    path,
                    section_errors,
                )
            else:
                section_kwargs[field.name] = _coerce_number(
                    value,
                    expected_type=type(getattr(section_type(), field.name)),
                    path=path,
                    errors=section_errors,
                )
        if section_errors:
            errors.extend(section_errors)
            continue
        kwargs[private_section] = section_type(**section_kwargs)
    if errors:
        return None
    return SimulationRules(**kwargs)


def _daily_limits_from_public(
    value: Any,
    path: str,
    errors: list[dict[str, str]],
) -> dict[CatalystActionType, int]:
    if not isinstance(value, dict):
        errors.append(_error(path, "Daily limits must be an object."))
        return {}
    limits: dict[CatalystActionType, int] = {}
    for action_type in CatalystActionType:
        action_path = f"{path}.{action_type.value}"
        raw_limit = value.get(action_type.value)
        if not _is_int(raw_limit) or int(raw_limit) < 0:
            errors.append(_error(action_path, "Daily limit must be a non-negative integer."))
            continue
        limits[action_type] = int(raw_limit)
    return limits


def _coerce_number(
    value: Any,
    *,
    expected_type: type,
    path: str,
    errors: list[dict[str, str]],
) -> int | float:
    if expected_type is int:
        if not _is_int(value):
            errors.append(_error(path, "Rule value must be an integer."))
            return 0
        return int(value)
    if not _is_number(value):
        errors.append(_error(path, "Rule value must be numeric."))
        return 0.0
    return float(value)


def _validate_semantics(
    rules: SimulationRules,
    errors: list[dict[str, str]],
    warnings: list[dict[str, str]],
) -> None:
    public_rules = rules_to_public(rules)
    _validate_number_ranges(public_rules, errors)
    _validate_min_max_pairs(public_rules, errors)

    if rules.region.recovery_stability_threshold <= rules.region.collapse_stability_threshold:
        errors.append(_error("region.recoveryStabilityThreshold", "Recovery stability must be above collapse stability."))
    if rules.region.recovery_resource_threshold <= rules.region.collapse_resource_threshold:
        errors.append(_error("region.recoveryResourceThreshold", "Recovery resource must be above collapse resource."))
    if rules.region.forced_collapse_stability > rules.region.collapse_stability_threshold:
        warnings.append(_warning("region.forcedCollapseStability", "Forced collapse stability is above the collapse threshold."))
    if rules.region.forced_collapse_resource > rules.region.collapse_resource_threshold:
        warnings.append(_warning("region.forcedCollapseResource", "Forced collapse resource is above the collapse threshold."))
    _validate_chirality_latch(rules.chirality, warnings)
    if rules.speciation.child_min_population > rules.speciation.candidate_min_population:
        errors.append(_error("speciation.childMinPopulation", "Child minimum population cannot exceed candidate minimum population."))
    if rules.speciation.child_population_fraction >= 1:
        errors.append(_error("speciation.childPopulationFraction", "Child population fraction must stay below 1."))


def _validate_chirality_latch(
    chirality: ChiralityRules,
    warnings: list[dict[str, str]],
) -> None:
    """Guard the two ways racemization can quietly hollow out the chirality tier.

    Neither is an error — starving a universe is a legitimate experiment — but
    both are invisible from the rules screen, so they get said out loud.
    """
    if chirality.racemization_rate >= chirality.amplify_k:
        warnings.append(
            _warning(
                "chirality.racemizationRate",
                "Racemization at or above amplifyK leaves the control parameter "
                "(amplifyK - racemizationRate) at or below zero, so racemic is stable: "
                "no region ever breaks symmetry and the life gate is unreachable.",
            )
        )
        return
    settled_ee = math.sqrt(1 - chirality.racemization_rate / chirality.amplify_k)
    if settled_ee < chirality.ee_lock_threshold:
        warnings.append(
            _warning(
                "chirality.racemizationRate",
                f"Regions settle near |ee| = {settled_ee:.2f}, short of the "
                f"{chirality.ee_lock_threshold} latch, so they may hover instead of "
                "locking. The life gate reads the universe mean, not the locks, so a "
                "universe here can still earn Stabilization while no lineage ever "
                "adopts a hand and the Organism Lens never unlocks. (Approximate: the "
                "latch is irreversible, so noise and the field can still carry regions "
                "over it — measured, latching survives to about 0.018.)",
            )
        )


def _validate_number_ranges(public_rules: dict[str, Any], errors: list[dict[str, str]]) -> None:
    for section_key, section in public_rules.items():
        for field_key, value in section.items():
            if isinstance(value, dict):
                for nested_key, nested_value in value.items():
                    _validate_numeric_value(
                        nested_value,
                        path=f"{section_key}.{field_key}.{nested_key}",
                        errors=errors,
                    )
                continue
            _validate_numeric_value(value, path=f"{section_key}.{field_key}", errors=errors)


def _validate_numeric_value(value: Any, *, path: str, errors: list[dict[str, str]]) -> None:
    if not _is_number(value):
        errors.append(_error(path, "Rule value must be numeric."))
        return
    number = float(value)
    if not math.isfinite(number):
        errors.append(_error(path, "Rule value must be finite."))
        return
    lower_path = path.lower()
    field_path = lower_path.rsplit(".", 1)[-1]
    if "dailylimits" in lower_path:
        if number < 0:
            errors.append(_error(path, "Daily limits must be non-negative."))
        return
    if "percent" in field_path:
        if number < 0 or number > 100:
            errors.append(_error(path, "Percent values must stay between 0 and 100."))
        return
    if "generation" in field_path or "window" in field_path:
        if number < 0:
            errors.append(_error(path, "Rule value must be non-negative."))
        return
    if any(token in field_path for token in ("interval", "ticks", "population", "scale", "divisor")):
        if number <= 0:
            errors.append(_error(path, "Rule value must be greater than 0."))
        return
    if "delta" in field_path:
        if number < -1 or number > 1:
            errors.append(_error(path, "Delta values must stay between -1 and 1."))
        return
    if number < 0 or number > 1:
        errors.append(_error(path, "Rule value must stay between 0 and 1."))


def _validate_min_max_pairs(public_rules: dict[str, Any], errors: list[dict[str, str]]) -> None:
    for section_key, section in public_rules.items():
        min_values: dict[str, float] = {}
        max_values: dict[str, float] = {}
        for field_key, value in section.items():
            if not _is_number(value):
                continue
            if field_key.endswith("Min"):
                min_values[field_key[:-3]] = float(value)
            elif field_key.endswith("Max"):
                max_values[field_key[:-3]] = float(value)
        for prefix, min_value in min_values.items():
            max_value = max_values.get(prefix)
            if max_value is not None and min_value > max_value:
                errors.append(_error(f"{section_key}.{prefix}Min", "Minimum value cannot exceed maximum value."))


def _result(
    rules: SimulationRules,
    errors: list[dict[str, str]],
    warnings: list[dict[str, str]],
) -> RuleValidationResult:
    public_rules = rules_to_public(rules)
    return RuleValidationResult(
        valid=not errors,
        rules=rules,
        public_rules=public_rules,
        rules_hash=rules_hash(rules),
        errors=errors,
        warnings=warnings,
    )


def _public_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            _public_key(key): _public_value(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_public_value(item) for item in value]
    if isinstance(value, CatalystActionType):
        return value.value
    return value


def _error(path: str, message: str) -> dict[str, str]:
    return {"path": path, "message": message}


def _warning(path: str, message: str) -> dict[str, str]:
    return {"path": path, "message": message}


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)
