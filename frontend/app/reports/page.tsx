import type { Metadata } from "next";
import { DynamicReportPanel } from "@/components/DynamicReportPanel";
import { EmptyState } from "@/components/EmptyState";
import { getDynamicReport, getRegions, getSpeciesList } from "@/lib/api";
import type { DynamicReportScope } from "@/lib/types";

export const metadata: Metadata = {
  title: "Reports | Evoverse",
  description: "Dynamic Alpha snapshot comparison and trend reports."
};

const REPORT_SCOPES = new Set(["universe", "region", "species"]);

export default async function ReportsPage({
  searchParams
}: {
  searchParams: Promise<{
    scope?: string;
    limit?: string;
    regionId?: string;
    speciesId?: string;
  }>;
}) {
  const params = await searchParams;
  const [regionsData, speciesData] = await Promise.all([getRegions(), getSpeciesList()]);
  const regions = regionsData?.regions ?? [];
  const species = speciesData?.species ?? [];
  const scope = parseScope(params.scope);
  const selectedRegionId = params.regionId ?? regions[0]?.id ?? null;
  const selectedSpeciesId = params.speciesId ?? species[0]?.id ?? null;
  const limit = parseLimit(params.limit);

  const report = await getDynamicReport({
    scope,
    limit,
    regionId: scope === "region" ? selectedRegionId : undefined,
    speciesId: scope === "species" ? selectedSpeciesId : undefined
  });

  if (!report) {
    return (
      <EmptyState
        title="Dynamic report is unavailable"
        message="Alpha needs snapshot coverage for the selected scope before this report can render."
      />
    );
  }

  return (
    <main className="page-shell reports-page">
      <DynamicReportPanel
        report={report}
        regions={regions}
        species={species}
        selectedRegionId={selectedRegionId}
        selectedSpeciesId={selectedSpeciesId}
      />
    </main>
  );
}

function parseScope(value: string | undefined): DynamicReportScope {
  return REPORT_SCOPES.has(value ?? "") ? (value as DynamicReportScope) : "universe";
}

function parseLimit(value: string | undefined) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return 12;
  }
  return Math.min(50, Math.max(1, Math.trunc(parsed)));
}
