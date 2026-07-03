"use client";

import { RouteErrorPanel } from "@/components/RouteErrorPanel";

export default function Error({ reset }: { reset: () => void }) {
  return (
    <RouteErrorPanel
      eyebrow="Dynamic Report"
      title="Report rendering failed"
      message="The selected snapshot range returned an unexpected report shape."
      reset={reset}
      homeHref="/universe"
    />
  );
}
