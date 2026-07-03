"use client";

import { RouteErrorPanel } from "@/components/RouteErrorPanel";

export default function Error({ reset }: { reset: () => void }) {
  return (
    <RouteErrorPanel
      eyebrow="Region"
      title="Region detail failed"
      message="The region record could not be rendered from the current Alpha response."
      reset={reset}
      homeHref="/universe"
    />
  );
}
