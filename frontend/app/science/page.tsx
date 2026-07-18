import type { Metadata } from "next";
import { CriticalityPanel } from "@/components/CriticalityPanel";
import { EmptyState } from "@/components/EmptyState";
import { MarkdownArticle } from "@/components/MarkdownArticle";
import { getDiagnostics } from "@/lib/api";
import { getMarkdownPage } from "@/lib/markdown";

export const metadata: Metadata = {
  title: "Science | Evoverse",
  description:
    "Does Alpha flock? The scale-free correlation measurement physicists ran on starling murmurations, applied to a simulated world — an honest null in space, and a genuine critical transition in its chirality."
};

export default async function SciencePage() {
  const [blocks, diagnostics] = await Promise.all([
    getMarkdownPage("science.md"),
    getDiagnostics()
  ]);

  return (
    <main className="page-shell info-page science-page">
      <MarkdownArticle blocks={blocks} eyebrow="Science" />
      {diagnostics ? (
        <CriticalityPanel data={diagnostics} />
      ) : (
        <EmptyState
          title="Diagnostics unavailable"
          message="The measurement runs against live state, so it comes back when Alpha does."
        />
      )}
    </main>
  );
}
