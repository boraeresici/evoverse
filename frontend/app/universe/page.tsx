import { EmptyState } from "@/components/EmptyState";
import { PageHelp } from "@/components/PageHelp";
import { StatusBand } from "@/components/StatusBand";
import { UniverseTimeExplorer } from "@/components/UniverseTimeExplorer";
import { getChronicle, getRegions, getSnapshots, getSpeciesList } from "@/lib/api";

const UNIVERSE_HELP = [
  {
    heading: "Hex map",
    body: "Each hexagon is a region placed by its real x/y coordinates, so neighbours are actually adjacent. Color encodes the selected mode; the whole field breathes with global stability."
  },
  {
    heading: "Map modes",
    body: "Life, Energy, Mutation, and Stability recolor the same regions by different metrics. Hover a hex for its dominant species and aggregate population; click to open the region."
  },
  {
    heading: "Event waves",
    body: "Recent events pulse outward to neighbouring regions, so mutation waves and collapses read spatially rather than as isolated dots."
  },
  {
    heading: "Time travel",
    body: "Drag the scrubber or press Play to redraw the map from historical snapshots. Era bands and Time Zoom frame the Alpha Age; Live returns to now."
  }
];

export default async function UniversePage() {
  const [data, speciesData, chronicleData, snapshots] = await Promise.all([
    getRegions(),
    getSpeciesList(),
    getChronicle("all"),
    getSnapshots({ limit: 100 })
  ]);

  if (!data) {
    return (
      <EmptyState
        title="Universe map is unavailable"
        message="Alpha signal is stabilizing. Try again after the backend finishes warming up."
      />
    );
  }

  return (
    <main className="page-shell">
      <StatusBand universe={data.universe} />
      <section className="page-title">
        <p className="eyebrow">Universe</p>
        <h1>Alpha Region Field</h1>
      </section>
      <PageHelp points={UNIVERSE_HELP} />
      <UniverseTimeExplorer
        liveRegions={data.regions}
        liveSpecies={speciesData?.species ?? []}
        liveEvents={chronicleData?.events ?? []}
        frames={snapshots?.snapshots ?? []}
      />
    </main>
  );
}
