"use client";

import Link from "next/link";
import { RefreshCw, TriangleAlert } from "lucide-react";

export function RouteErrorPanel({
  eyebrow,
  title,
  message,
  reset,
  homeHref = "/"
}: {
  eyebrow: string;
  title: string;
  message: string;
  reset: () => void;
  homeHref?: string;
}) {
  return (
    <main className="page-shell">
      <section className="route-feedback route-error">
        <TriangleAlert size={30} aria-hidden="true" />
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p>{message}</p>
        <div className="route-actions">
          <button className="secondary-action route-action-button" type="button" onClick={reset}>
            <RefreshCw size={17} aria-hidden="true" />
            Retry
          </button>
          <Link className="secondary-action" href={homeHref}>
            Back to observatory
          </Link>
        </div>
      </section>
    </main>
  );
}
