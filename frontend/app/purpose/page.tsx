import type { Metadata } from "next";
import { MarkdownArticle } from "@/components/MarkdownArticle";
import { getMarkdownPage } from "@/lib/markdown";

export const metadata: Metadata = {
  title: "Purpose | Evoverse",
  description: "Why Evoverse exists and what Alpha is designed to observe."
};

export default async function PurposePage() {
  const blocks = await getMarkdownPage("purpose.md");

  return (
    <main className="page-shell info-page">
      <MarkdownArticle blocks={blocks} eyebrow="Purpose" />
    </main>
  );
}
