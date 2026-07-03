import type { SpeciesDetail } from "./types";

export const CARD_WIDTH = 480;
export const CARD_HEIGHT = 300;

const STATUS_COLORS: Record<string, string> = {
  emerging: "#1b87a5",
  stable: "#3c8c66",
  dominant: "#315f9b",
  declining: "#c88a24",
  extinct: "#b6533e"
};

const TRAIT_ORDER = ["efficiency", "adaptation", "cooperation", "mobility", "resilience"];

/**
 * Build a self-contained, style-inlined SVG "species card" string. The same
 * markup is used both for the on-page preview and for PNG rasterization, so it
 * must not depend on external CSS or fonts.
 */
export function buildSpeciesCardSvg(data: SpeciesDetail): string {
  const species = data.species;
  const accent = STATUS_COLORS[species.status] ?? "#66716d";
  const name = truncate(species.name, 22);
  const traits = orderedTraits(species.traits);
  const font = "Inter, system-ui, -apple-system, Segoe UI, sans-serif";

  const traitRows = traits
    .map((trait, index) => {
      const y = 150 + index * 26;
      const width = Math.round(clamp01(trait.value) * 150);
      return `
        <text x="34" y="${y + 4}" font-size="12" font-weight="700" fill="#52605b" font-family="${font}">${escapeXml(
          titleize(trait.key)
        )}</text>
        <rect x="150" y="${y - 8}" width="150" height="12" rx="6" fill="#ece7db" />
        <rect x="150" y="${y - 8}" width="${width}" height="12" rx="6" fill="${accent}" />
        <text x="312" y="${y + 4}" font-size="12" font-weight="800" fill="#18211f" font-family="${font}">${Math.round(
          clamp01(trait.value) * 100
        )}%</text>`;
    })
    .join("");

  const forecast = [
    { label: "Extinction", value: species.forecast.extinctionRisk },
    { label: "Dominance", value: species.forecast.dominanceProbability },
    { label: "Expansion", value: species.forecast.expansionPressure },
    { label: "Mutation", value: species.forecast.mutationVolatility }
  ];
  const forecastChips = forecast
    .map((item, index) => {
      const x = 340;
      const y = 132 + index * 30;
      return `
        <text x="${x}" y="${y}" font-size="11" font-weight="700" fill="#66716d" font-family="${font}">${escapeXml(
          item.label
        )}</text>
        <text x="${x + 120}" y="${y}" font-size="13" font-weight="800" fill="#18211f" text-anchor="end" font-family="${font}">${Math.round(
          clamp01(item.value) * 100
        )}%</text>`;
    })
    .join("");

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${CARD_WIDTH}" height="${CARD_HEIGHT}" viewBox="0 0 ${CARD_WIDTH} ${CARD_HEIGHT}" role="img" aria-label="${escapeXml(
    species.name
  )} species card">
  <rect x="1" y="1" width="${CARD_WIDTH - 2}" height="${CARD_HEIGHT - 2}" rx="16" fill="#fffdf8" stroke="#d8d4c9" stroke-width="1.5" />
  <rect x="1" y="1" width="${CARD_WIDTH - 2}" height="8" rx="4" fill="${accent}" />
  <text x="34" y="46" font-size="11" font-weight="800" letter-spacing="2" fill="#66716d" font-family="${font}">EVOVERSE ALPHA · SPECIES</text>
  <text x="34" y="76" font-size="26" font-weight="900" fill="#18211f" font-family="${font}">${escapeXml(name)}</text>
  <rect x="34" y="90" width="${badgeWidth(species.status)}" height="22" rx="11" fill="${accent}" />
  <text x="${34 + badgeWidth(species.status) / 2}" y="105" font-size="11" font-weight="800" fill="#ffffff" text-anchor="middle" font-family="${font}">${escapeXml(
    species.status.toUpperCase()
  )}</text>
  <text x="${34 + badgeWidth(species.status) + 14}" y="105" font-size="12" font-weight="700" fill="#52605b" font-family="${font}">Generation ${species.generation}</text>
  <text x="340" y="60" font-size="11" font-weight="700" fill="#66716d" font-family="${font}">Population</text>
  <text x="446" y="60" font-size="20" font-weight="900" fill="#18211f" text-anchor="end" font-family="${font}">${abbreviate(
    species.population
  )}</text>
  <text x="340" y="82" font-size="11" font-weight="700" fill="#66716d" font-family="${font}">Origin</text>
  <text x="446" y="82" font-size="12" font-weight="800" fill="#18211f" text-anchor="end" font-family="${font}">${escapeXml(
    species.originRegionId
  )}</text>
  <line x1="34" y1="120" x2="446" y2="120" stroke="#ece7db" stroke-width="1" />
  ${traitRows}
  ${forecastChips}
  <text x="34" y="284" font-size="10" font-weight="700" fill="#8a938f" font-family="${font}">Emerged · Age ${species.emergedAtWorldAge.toLocaleString()}</text>
  <text x="446" y="284" font-size="10" font-weight="700" fill="#8a938f" text-anchor="end" font-family="${font}">${escapeXml(
    species.id
  )}</text>
</svg>`;
}

function orderedTraits(traits: Record<string, number>): Array<{ key: string; value: number }> {
  const known = TRAIT_ORDER.filter((key) => key in traits).map((key) => ({
    key,
    value: Number(traits[key])
  }));
  const remaining = Object.entries(traits)
    .filter(([key]) => !TRAIT_ORDER.includes(key))
    .map(([key, value]) => ({ key, value: Number(value) }));
  return [...known, ...remaining].slice(0, 5);
}

function badgeWidth(status: string): number {
  return Math.max(56, status.length * 8 + 20);
}

function abbreviate(value: number): string {
  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1)}M`;
  }
  if (value >= 1_000) {
    return `${(value / 1_000).toFixed(1)}K`;
  }
  return value.toLocaleString();
}

function clamp01(value: number): number {
  return Math.max(0, Math.min(1, Number(value) || 0));
}

function truncate(value: string, max: number): string {
  return value.length > max ? `${value.slice(0, max - 1)}…` : value;
}

function titleize(value: string): string {
  return value.replace(/([A-Z])/g, " $1").replace(/^./, (letter) => letter.toUpperCase());
}

function escapeXml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}
