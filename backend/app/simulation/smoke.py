from __future__ import annotations

from collections import Counter

from app.simulation import SimulationEngine, seed_alpha


def main() -> None:
    state = seed_alpha()
    engine = SimulationEngine(seed=state.seed)
    engine.advance(state, ticks=120)
    event_counts = Counter(event.event_type.value for event in state.events)
    print(f"Alpha Age: {state.universe.age_years}")
    print(f"Regions: {len(state.regions)}")
    print(f"Species: {len(state.species)}")
    print(f"Events: {len(state.events)}")
    print("Event Types:")
    for event_type, count in sorted(event_counts.items()):
        print(f"  {event_type}: {count}")


if __name__ == "__main__":
    main()
