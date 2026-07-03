import Link from "next/link";
import { ArrowRight, GitBranch } from "lucide-react";
import type { SpeciesSummary } from "@/lib/types";

type SpeciesStripProps = {
  species: SpeciesSummary[];
};

export function SpeciesStrip({ species }: SpeciesStripProps) {
  return (
    <div className="species-strip">
      {species.map((item) => (
        <Link className="species-chip" href={`/species/${item.id}`} key={item.id}>
          <GitBranch size={16} aria-hidden="true" />
          <span>
            <strong>{item.name}</strong>
            <small>{item.population.toLocaleString()} population</small>
          </span>
          <ArrowRight size={15} aria-hidden="true" />
        </Link>
      ))}
    </div>
  );
}
