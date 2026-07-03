import type { Metadata } from "next";
import { EmptyState } from "@/components/EmptyState";
import { RegionComparePanel } from "@/components/RegionComparePanel";
import { getDynamicReport, getRegions } from "@/lib/api";

export const metadata: Metadata = {
  title: "Compare Regions | Evoverse",
  description: "Compare Alpha regions across population, species, resources, and stability."
};

export default async function ComparePage({
  searchParams
}: {
  searchParams: Promise<{ left?: string; right?: string }>;
}) {
  const params = await searchParams;
  const regionsData = await getRegions();
  const regions = regionsData?.regions ?? [];

  if (!regions.length) {
    return <EmptyState title="Region comparison unavailable" />;
  }

  const leftRegionId = params.left ?? regions[0].id;
  const rightRegionId = params.right ?? regions[1]?.id ?? regions[0].id;
  const [leftReport, rightReport] = await Promise.all([
    getDynamicReport({ scope: "region", regionId: leftRegionId, limit: 12 }),
    getDynamicReport({ scope: "region", regionId: rightRegionId, limit: 12 })
  ]);

  return (
    <main className="page-shell reports-page">
      <RegionComparePanel
        regions={regions}
        leftRegionId={leftRegionId}
        rightRegionId={rightRegionId}
        leftReport={leftReport}
        rightReport={rightReport}
      />
    </main>
  );
}

