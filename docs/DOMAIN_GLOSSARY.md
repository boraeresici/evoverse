# Evoverse Domain Glossary

## Universe

The top-level simulation space. Phase-1 runs only Alpha, but the code keeps the boundary open for Beta and Gamma.

## Region

A grid cell inside a universe. Regions own biome, energy, resource density, stability, and dominant species state.

## Species

A species-level life form. Phase-1 does not simulate individual organisms; species are tracked through aggregate populations per region.

## Population

The aggregate count of a species inside a region. Population growth, decline, migration pressure, mutation chances, and event generation operate from this layer.

## Traits

Numerical properties that influence species behavior:

- efficiency
- adaptation
- cooperation
- mobility
- resilience

## Event

A durable simulation fact used by Chronicle, Region/Species timelines, Replay Lite, Forecast Lite, and future Time Zoom.

## Catalyst Action

A limited, regional user influence. It never creates species directly and never applies globally.
