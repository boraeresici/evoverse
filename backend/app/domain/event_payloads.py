from __future__ import annotations

from collections.abc import Mapping
from typing import Any


EVENT_PAYLOAD_SCHEMA_VERSION = 1
EVENT_PAYLOAD_SCHEMA_NAMESPACE = "event_payload"
EVENT_PAYLOAD_SCHEMA_VERSION_KEY = "schemaVersion"

EVENT_PAYLOAD_CONTRACTS: dict[str, dict[str, Any]] = {
    "species_emerged": {
        "required": ("generation",),
        "optional": ("parent_species_id",),
        "description": "A new species became observable in a region.",
    },
    "species_declined": {
        "required": ("decline_percent",),
        "optional": (),
        "description": "A species population dropped enough to be chronicle-worthy.",
    },
    "mutation_detected": {
        "required": (),
        "optional": ("child_species_id", "trait_deltas", "chiral_flip"),
        "description": "A mutation pressure or branch was detected for a species.",
    },
    "region_resource_shift": {
        "required": ("direction",),
        "optional": ("from", "to"),
        "description": "A region resource density changed materially.",
    },
    "region_collapse": {
        "required": (),
        "optional": (),
        "description": "A region crossed collapse thresholds.",
    },
    "catalyst_action": {
        "required": ("action_type", "action_id", "user_id"),
        "optional": ("day_key",),
        "description": "A user-triggered catalyst action was accepted.",
    },
    "symmetry_break": {
        "required": ("scope",),
        "optional": ("hand", "hand_sign", "homochirality_index"),
        "description": "Chiral symmetry broke: a region, lineage, or the whole "
        "universe latched to a single handedness.",
    },
}


def event_payload_schema(event_type: Any, version: int = EVENT_PAYLOAD_SCHEMA_VERSION) -> str:
    return f"{EVENT_PAYLOAD_SCHEMA_NAMESPACE}.{_event_type_value(event_type)}.v{version}"


def version_event_payload(
    event_type: Any,
    payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Return an additive, v1-compatible payload envelope."""
    event_value = _event_type_value(event_type)
    normalized = dict(payload or {})
    version = _payload_version(normalized.get(EVENT_PAYLOAD_SCHEMA_VERSION_KEY))
    normalized[EVENT_PAYLOAD_SCHEMA_VERSION_KEY] = version
    normalized["schema"] = normalized.get("schema") or event_payload_schema(
        event_value,
        version,
    )
    normalized["eventType"] = normalized.get("eventType") or event_value
    return normalized


def validate_event_payload(event_type: Any, payload: Mapping[str, Any]) -> list[dict[str, str]]:
    event_value = _event_type_value(event_type)
    contract = EVENT_PAYLOAD_CONTRACTS.get(event_value)
    if contract is None:
        return [{"path": "eventType", "message": f"Unknown event type: {event_value}"}]

    errors: list[dict[str, str]] = []
    schema_version = payload.get(EVENT_PAYLOAD_SCHEMA_VERSION_KEY)
    if schema_version != EVENT_PAYLOAD_SCHEMA_VERSION:
        errors.append(
            {
                "path": EVENT_PAYLOAD_SCHEMA_VERSION_KEY,
                "message": f"Expected schema version {EVENT_PAYLOAD_SCHEMA_VERSION}.",
            }
        )
    expected_schema = event_payload_schema(event_value)
    if payload.get("schema") != expected_schema:
        errors.append({"path": "schema", "message": f"Expected schema {expected_schema}."})
    if payload.get("eventType") != event_value:
        errors.append({"path": "eventType", "message": f"Expected event type {event_value}."})

    for field_name in contract["required"]:
        if payload.get(field_name) is None:
            errors.append({"path": field_name, "message": "Required field is missing."})
    return errors


def _event_type_value(event_type: Any) -> str:
    return str(getattr(event_type, "value", event_type))


def _payload_version(value: Any) -> int:
    if value is None:
        return EVENT_PAYLOAD_SCHEMA_VERSION
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        candidate = value.lower().removeprefix("v")
        if candidate.isdigit():
            return int(candidate)
    return EVENT_PAYLOAD_SCHEMA_VERSION
