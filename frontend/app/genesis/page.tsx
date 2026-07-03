import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, Dna, GitBranch, Orbit, Sparkles } from "lucide-react";
import { GenesisLifePreview } from "@/components/GenesisLifePreview";
import { MarkdownArticle } from "@/components/MarkdownArticle";
import { getMarkdownPage } from "@/lib/markdown";

export const metadata: Metadata = {
  title: "Genesis | Evoverse",
  description: "How Alpha begins and why Evoverse turns Conway's seed idea into aggregate ecology."
};

const stages = [
  {
    title: "Seed",
    text: "A deterministic starting field gives Alpha repeatable first conditions.",
    icon: Sparkles
  },
  {
    title: "Regions",
    text: "Cells become aggregate regions with energy, resources, stability, and collapse pressure.",
    icon: Orbit
  },
  {
    title: "Species",
    text: "Population edges and traits turn the field into evolving lineages.",
    icon: Dna
  },
  {
    title: "History",
    text: "Events and snapshots make the first life readable after it starts moving.",
    icon: GitBranch
  }
];

export default async function GenesisPage() {
  const blocks = await getMarkdownPage("genesis.md");

  return (
    <main className="page-shell info-page genesis-page">
      <section className="genesis-stage" aria-label="Genesis stages">
        <div>
          <p className="eyebrow">Alpha Genesis</p>
          <h1>From seed to living observatory.</h1>
          <p>
            Evoverse starts with Conway&apos;s emergence instinct, then turns the first cell field into
            species, regions, resources, interventions, and history.
          </p>
          <Link className="primary-action" href="/universe">
            Enter Alpha
            <ArrowRight size={16} aria-hidden="true" />
          </Link>
        </div>
        <div className="genesis-stage-visual">
          <GenesisLifePreview />
          <div className="genesis-stage-grid">
            {stages.map((stage, index) => {
              const Icon = stage.icon;
              return (
                <article key={stage.title}>
                  <span>{String(index + 1).padStart(2, "0")}</span>
                  <Icon size={18} aria-hidden="true" />
                  <h2>{stage.title}</h2>
                  <p>{stage.text}</p>
                </article>
              );
            })}
          </div>
        </div>
      </section>
      <MarkdownArticle blocks={blocks} eyebrow="Genesis Notes" />
    </main>
  );
}
