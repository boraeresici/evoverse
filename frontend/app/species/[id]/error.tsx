"use client";

import { RouteErrorPanel } from "@/components/RouteErrorPanel";

export default function Error({ reset }: { reset: () => void }) {
  return (
    <RouteErrorPanel
      eyebrow="Species"
      title="Species detail failed"
      message="The lineage response could not be rendered from the current Alpha state."
      reset={reset}
      homeHref="/universe"
    />
  );
}
