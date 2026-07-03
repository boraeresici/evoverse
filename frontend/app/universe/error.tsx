"use client";

import { RouteErrorPanel } from "@/components/RouteErrorPanel";

export default function Error({ reset }: { reset: () => void }) {
  return (
    <RouteErrorPanel
      eyebrow="Universe"
      title="Universe map failed"
      message="The region field returned an unexpected signal. Retry after Alpha settles."
      reset={reset}
      homeHref="/"
    />
  );
}
