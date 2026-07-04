import type { Metadata } from "next";
import { InfoStatement } from "@/components/InfoStatement";
import { MarkdownArticle } from "@/components/MarkdownArticle";
import { getMarkdownPage } from "@/lib/markdown";

export const metadata: Metadata = {
  title: "Resources | Evoverse",
  description: "Scientific and conceptual references behind Evoverse Alpha."
};

export default async function ResourcesPage() {
  const blocks = await getMarkdownPage("resources.md");

  return (
    <main className="page-shell info-page info-split">
      <MarkdownArticle blocks={blocks} eyebrow="Resources" />
      <InfoStatement
        eyebrow="Reference shelf"
        headline="References, not replicas."
        text="Cellular automata, astrobiology, evolution, and artificial-life research are orientation points — Evoverse combines them into its own legible, product-facing ecology."
        cta={{ href: "/genesis", label: "See Genesis" }}
      />
    </main>
  );
}
