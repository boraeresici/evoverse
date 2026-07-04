import type { Metadata } from "next";
import { InfoStatement } from "@/components/InfoStatement";
import { MarkdownArticle } from "@/components/MarkdownArticle";
import { getMarkdownPage } from "@/lib/markdown";

export const metadata: Metadata = {
  title: "Purpose | Evoverse",
  description: "Why Evoverse exists and what Alpha is designed to observe."
};

export default async function PurposePage() {
  const blocks = await getMarkdownPage("purpose.md");

  return (
    <main className="page-shell info-page info-split">
      <MarkdownArticle blocks={blocks} eyebrow="Purpose" />
      <InfoStatement
        eyebrow="Why Evoverse"
        headline="Emergence you can read."
        text="Evoverse keeps Conway's spark, then raises every cell into an ecology you can question — what changed, where a species moved, and why a region collapsed."
        cta={{ href: "/universe", label: "Enter Alpha" }}
      />
    </main>
  );
}
