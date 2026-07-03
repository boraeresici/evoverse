import { LoaderCircle } from "lucide-react";

export function LoadingState({
  eyebrow,
  title,
  message
}: {
  eyebrow: string;
  title: string;
  message: string;
}) {
  return (
    <main className="page-shell">
      <section className="route-feedback" aria-live="polite" aria-busy="true">
        <LoaderCircle className="route-spinner" size={28} aria-hidden="true" />
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p>{message}</p>
      </section>
    </main>
  );
}
