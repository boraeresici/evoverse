import type { Metadata } from "next";
import { MarkdownArticle } from "@/components/MarkdownArticle";
import { getMarkdownPage } from "@/lib/markdown";

export const metadata: Metadata = {
  title: "Resources | Evoverse",
  description: "Scientific and conceptual references behind Evoverse Alpha."
};

export default async function ResourcesPage() {
  const blocks = await getMarkdownPage("resources.md");

  return (
    <main className="page-shell info-page">
      <MarkdownArticle blocks={blocks} eyebrow="Resources" />
    </main>
  );
}
