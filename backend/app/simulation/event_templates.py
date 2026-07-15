from __future__ import annotations

from app.domain import CatalystActionType, Era, EventType, Region, Species


def species_emerged(species: Species, parent: Species | None, region: Region) -> tuple[str, str]:
    parent_text = f" from {parent.name}" if parent else ""
    return (
        f"New species emerged: {species.name}",
        f"{species.name}{parent_text} stabilized in {region.id} as Alpha crossed a new adaptive threshold.",
    )


def mutation_detected(species: Species, region: Region) -> tuple[str, str]:
    return (
        f"Mutation wave detected near {region.id}",
        f"{species.name} shows measurable trait drift around the {region.biome_type.value.replace('_', ' ')} biome.",
    )


def species_declined(species: Species, decline_percent: int) -> tuple[str, str]:
    return (
        f"{species.name} population declined",
        f"{species.name} lost {decline_percent}% of its known population as regional pressure increased.",
    )


def region_resource_shift(region: Region, direction: str) -> tuple[str, str]:
    verb = "rose" if direction == "rise" else "fell"
    return (
        f"Resource shift in {region.id}",
        f"Resource density {verb} across {region.id}, changing local migration pressure.",
    )


def region_collapse(region: Region) -> tuple[str, str]:
    return (
        f"{region.id} collapsed",
        f"{region.id} entered collapse after stability and resources fell below viability.",
    )


def _hand_label(hand_sign: int) -> str:
    return "right-handed" if hand_sign >= 0 else "left-handed"


def symmetry_break_region(region: Region, hand_sign: int) -> tuple[str, str]:
    return (
        f"Chiral symmetry broke in {region.id}",
        f"{region.id} latched to a {_hand_label(hand_sign)} chirality — the first "
        f"molecular symmetry break in Alpha, now irreversible.",
    )


def symmetry_break_lineage(species: Species, hand_sign: int) -> tuple[str, str]:
    return (
        f"{species.name} committed to a chirality",
        f"{species.name} adopted a {_hand_label(hand_sign)} hand from its origin "
        f"region — heritable chiral information now flows down its lineage.",
    )


def symmetry_break_universe(homochirality_index: float) -> tuple[str, str]:
    return (
        "Alpha reached full homochirality",
        f"Every viable region has latched to a single hand (homochirality index "
        f"{homochirality_index:.2f}). Alpha crossed the chemistry-to-life threshold.",
    )


def era_advanced(from_era: Era, to_era: Era, homochirality_index: float) -> tuple[str, str]:
    return (
        f"Alpha entered the {to_era.value}",
        f"Homochirality reached {homochirality_index:.2f}; Alpha advanced from the "
        f"{from_era.value} to the {to_era.value} — a threshold it earned, not one it was given.",
    )


def catalyst_action(action_type: CatalystActionType, region: Region) -> tuple[str, str]:
    labels = {
        CatalystActionType.ENERGY_PULSE: "Energy Pulse",
        CatalystActionType.MUTATION_PULSE: "Mutation Pulse",
        CatalystActionType.RESOURCE_BURST: "Resource Burst",
    }
    label = labels[action_type]
    return (
        f"{label} initiated in {region.id}",
        f"A regional catalyst influence began in {region.id}. Alpha will decide the downstream effect.",
    )


EVENT_TYPE_LABELS: dict[EventType, str] = {
    EventType.SPECIES_EMERGED: "Species emerged",
    EventType.SPECIES_DECLINED: "Species declined",
    EventType.MUTATION_DETECTED: "Mutation detected",
    EventType.REGION_RESOURCE_SHIFT: "Resource shift",
    EventType.REGION_COLLAPSE: "Region collapse",
    EventType.CATALYST_ACTION: "Catalyst action",
    EventType.SYMMETRY_BREAK: "Symmetry break",
    EventType.ERA_ADVANCED: "Era advanced",
}
