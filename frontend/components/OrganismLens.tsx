"use client";

/**
 * Organism Lens shell: decides whether a lineage may be inspected, and only then
 * pulls in the renderer.
 *
 * `ssr: false` alone would still ship three in this route's client bundle the
 * moment the shell mounts — and this shell sits on every species page. The
 * import is therefore gated behind `open`, so three (~150 KB gzipped) downloads
 * when an observer actually asks for a body, and never otherwise.
 */

import dynamic from "next/dynamic";
import { useMemo, useState } from "react";
import { Lock, LoaderCircle, Maximize2, X } from "lucide-react";
import { deriveBodyParams, deriveFormState, resolveLensMode } from "@/lib/organismLens";
import type { RegionSummary, SpeciesSummary } from "@/lib/types";

// Not `LoadingState`: that renders a full-page <main>, which would nest inside
// the species page's own. The Lens needs an inline placeholder the size of the
// stage it is about to fill.
const OrganismLensCanvas = dynamic(() => import("@/components/OrganismLensCanvas"), {
  ssr: false,
  loading: () => (
    <div className="lens-stage lens-stage-loading" aria-busy="true">
      <LoaderCircle className="route-spinner" size={22} aria-hidden="true" />
      <small>Resolving the lineage&apos;s form…</small>
    </div>
  )
});

type OrganismLensProps = {
  species: SpeciesSummary;
  originRegion: RegionSummary | null;
};

/** Stable per-lineage tint, mirroring how the micro field colours species. */
function speciesHue(id: string): number {
  let hash = 2166136261;
  for (let index = 0; index < id.length; index += 1) {
    hash ^= id.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0) % 360;
}

export function OrganismLens({ species, originRegion }: OrganismLensProps) {
  const [open, setOpen] = useState(false);

  const lens = useMemo(
    () => resolveLensMode({ species, originRegion }),
    [species, originRegion]
  );
  // Geometry depends only on lifetime-fixed state, so it survives ticks; the
  // form state is cheap and rebuilt whenever load moves.
  const body = useMemo(() => deriveBodyParams(species), [species]);
  const form = useMemo(() => deriveFormState(species), [species]);
  const hue = useMemo(() => speciesHue(species.id), [species.id]);

  if (lens.mode === "locked") {
    return (
      <div className="lens-locked">
        <Lock size={15} aria-hidden="true" />
        <span>
          <strong>Inspect locked</strong>
          <small>{lens.reason}</small>
        </span>
      </div>
    );
  }

  const hand = species.chirality > 0 ? "right" : species.chirality < 0 ? "left" : "unhanded";

  return (
    <div className="lens-shell">
      {open ? (
        <>
          <div className="lens-head">
            <span className="eyebrow">Organism Lens</span>
            <button className="secondary-action" onClick={() => setOpen(false)} type="button">
              <X size={15} aria-hidden="true" />
              Close
            </button>
          </div>
          <OrganismLensCanvas body={body} form={form} mode={lens.mode} hue={hue} />
          <dl className="lens-readout">
            <div>
              <dt>Hand</dt>
              <dd>{hand}-coiled</dd>
            </div>
            <div>
              <dt>Coherence</dt>
              <dd>{Math.round(form.coherence * 100)}%</dd>
            </div>
            <div>
              <dt>Segments</dt>
              <dd>{body.segments}</dd>
            </div>
          </dl>
          {form.failing ? (
            <p className="lens-warning">
              This lineage carries a lethal heterochiral load — its form is coming apart.
            </p>
          ) : null}
        </>
      ) : (
        <button className="lens-open" onClick={() => setOpen(true)} type="button">
          <Maximize2 size={16} aria-hidden="true" />
          <span>
            <strong>Inspect the organism</strong>
            <small>{lens.reason}</small>
          </span>
        </button>
      )}
    </div>
  );
}
