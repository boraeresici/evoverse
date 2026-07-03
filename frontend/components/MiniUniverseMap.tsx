import Link from "next/link";
import type { CSSProperties } from "react";
import { lifeTextureVars } from "@/lib/lifeTexture";
import type { RegionSummary } from "@/lib/types";

type MiniUniverseMapProps = {
  regions: RegionSummary[];
};

export function MiniUniverseMap({ regions }: MiniUniverseMapProps) {
  return (
    <div className="map-shell">
      <div className="map-toolbar">
        <span>Life</span>
        <span>Energy</span>
        <span>Stability</span>
      </div>
      <div className="universe-grid" aria-label="Alpha region map">
        {regions.map((region) => (
          <Link
            aria-label={`${region.id}, ${region.dominantSpeciesName ?? "no dominant species"}, aggregate life field`}
            className={region.collapsed ? "region-cell collapsed" : "region-cell"}
            href={`/regions/${region.id}`}
            key={region.id}
            style={{
              "--life": region.lifeIndex,
              "--energy": region.energyLevel,
              "--stability": region.stability,
              "--risk": 1 - region.stability,
              "--mutation": 0,
              ...lifeTextureVars(region, {
                diversity: region.dominantSpeciesId ? 0.28 : 0.08
              })
            } as CSSProperties}
            title={`${region.id} / ${region.biomeType}`}
          >
            <span className="region-life-texture" aria-hidden="true" />
          </Link>
        ))}
      </div>
    </div>
  );
}
