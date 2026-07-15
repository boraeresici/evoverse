from __future__ import annotations

from app.domain import AlphaState, Event, Population, Region, Species
from app.domain.event_payloads import EVENT_PAYLOAD_SCHEMA_VERSION, event_payload_schema
from app.simulation.event_templates import EVENT_TYPE_LABELS


def serialize_universe(state: AlphaState) -> dict:
    active_species = [
        species for species in state.species.values() if species.status.value != "extinct"
    ]
    recent_events = state.events[-24:]
    return {
        "id": state.universe.id,
        "name": state.universe.name,
        "ageYears": state.universe.age_years,
        "currentEra": state.universe.current_era.value,
        "activeSpecies": len(active_species),
        "regionCount": len(state.regions),
        "recentEvents": len(recent_events),
        "stabilityIndex": round(state.universe.stability_index, 3),
        "chiralityEe": round(state.universe.chirality_ee, 4),
        "homochiralityIndex": round(state.universe.homochirality_index, 4),
        "chiralityLocked": state.universe.chirality_locked,
    }


def serialize_event(event: Event, state: AlphaState) -> dict:
    species = state.species.get(event.species_id or "")
    region = state.regions.get(event.region_id or "")
    payload = event.payload
    return {
        "id": event.id,
        "eventType": event.event_type.value,
        "eventLabel": EVENT_TYPE_LABELS[event.event_type],
        "severity": event.severity,
        "worldAge": event.world_age,
        "title": event.title,
        "summary": event.summary,
        "regionId": event.region_id,
        "regionName": region.id if region else None,
        "speciesId": event.species_id,
        "speciesName": species.name if species else None,
        "payload": payload,
        "payloadSchemaVersion": payload.get(
            "schemaVersion",
            EVENT_PAYLOAD_SCHEMA_VERSION,
        ),
        "payloadSchema": payload.get("schema", event_payload_schema(event.event_type)),
        "createdAt": event.created_at,
    }


def serialize_region(region: Region, state: AlphaState) -> dict:
    dominant_species = state.species.get(region.dominant_species_id or "")
    populations = [
        population
        for population in state.populations.values()
        if population.region_id == region.id and population.population_count > 0
    ]
    total_population = sum(item.population_count for item in populations)
    life_index = min(1.0, total_population / 26000)
    return {
        "id": region.id,
        "x": region.x,
        "y": region.y,
        "biomeType": region.biome_type.value,
        "energyLevel": region.energy_level,
        "resourceDensity": region.resource_density,
        "stability": region.stability,
        "lifeIndex": round(life_index, 3),
        "chiralityEe": round(region.chirality_ee, 4),
        "chiralityLocked": region.chirality_locked,
        "collapsed": region.collapsed,
        "dominantSpeciesId": dominant_species.id if dominant_species else None,
        "dominantSpeciesName": dominant_species.name if dominant_species else None,
        "population": total_population,
    }


def serialize_population(population: Population, state: AlphaState) -> dict:
    species = state.species[population.species_id]
    return {
        "speciesId": species.id,
        "speciesName": species.name,
        "status": species.status.value,
        "population": population.population_count,
        "growthRate": population.growth_rate,
        "migrationPressure": population.migration_pressure,
    }


def serialize_species(species: Species, state: AlphaState) -> dict:
    populations = [
        population
        for population in state.populations.values()
        if population.species_id == species.id and population.population_count > 0
    ]
    total_population = sum(item.population_count for item in populations)
    regions = sorted(
        [
            {
                "regionId": population.region_id,
                "population": population.population_count,
                "share": round(population.population_count / total_population, 3)
                if total_population
                else 0,
            }
            for population in populations
        ],
        key=lambda item: item["population"],
        reverse=True,
    )
    return {
        "id": species.id,
        "name": species.name,
        "status": species.status.value,
        "population": total_population,
        "originRegionId": species.origin_region_id,
        "emergedAtWorldAge": species.emerged_at_world_age,
        "generation": species.generation,
        "parentSpeciesId": species.parent_species_id,
        "chirality": species.chirality,
        "heterochiralLoad": round(species.heterochiral_load, 4),
        "traits": species.traits.to_public(),
        "regions": regions[:12],
        "forecast": serialize_species_forecast(species, state),
    }


def serialize_species_forecast(species: Species, state: AlphaState) -> dict:
    total_population = sum(
        population.population_count
        for population in state.populations.values()
        if population.species_id == species.id and population.population_count > 0
    )
    return _forecast_lite(species, state, total_population)


def _forecast_lite(species: Species, state: AlphaState, total_population: int) -> dict:
    related_regions = [
        state.regions[population.region_id]
        for population in state.populations.values()
        if population.species_id == species.id and population.population_count > 0
    ]
    if not related_regions:
        return {
            "extinctionRisk": 0.96,
            "dominanceProbability": 0.02,
            "expansionPressure": 0.0,
            "mutationVolatility": 0.0,
        }
    avg_energy = sum(region.energy_level for region in related_regions) / len(related_regions)
    avg_stability = sum(region.stability for region in related_regions) / len(related_regions)
    trait_strength = sum(species.traits.to_public().values()) / 5
    extinction_risk = max(0.03, min(0.94, 1 - (avg_energy * 0.34 + avg_stability * 0.28 + trait_strength * 0.3)))
    dominance_probability = min(0.95, (total_population / 120000) + trait_strength * 0.34)
    expansion_pressure = min(0.98, species.traits.mobility * 0.55 + avg_energy * 0.25)
    mutation_volatility = min(0.98, (1 - avg_stability) * 0.4 + species.traits.adaptation * 0.28)
    return {
        "extinctionRisk": round(extinction_risk, 3),
        "dominanceProbability": round(dominance_probability, 3),
        "expansionPressure": round(expansion_pressure, 3),
        "mutationVolatility": round(mutation_volatility, 3),
    }
