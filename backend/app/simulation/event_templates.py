from __future__ import annotations

from app.domain import CatalystActionType, EventType, Region, Species


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
}
