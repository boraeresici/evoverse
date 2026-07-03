"use client";

import { RouteErrorPanel } from "@/components/RouteErrorPanel";

export default function Error({ reset }: { reset: () => void }) {
  return (
    <RouteErrorPanel
      eyebrow="Compare"
      title="Region comparison failed"
      message="The selected regions could not be compared from the current report response."
      reset={reset}
      homeHref="/reports"
    />
  );
}
