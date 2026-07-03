export function EmptyState({
  title,
  message = "Alpha signal is stabilizing."
}: {
  title: string;
  message?: string;
}) {
  return (
    <main className="page-shell">
      <section className="empty-state">
        <h1>{title}</h1>
        <p>{message}</p>
      </section>
    </main>
  );
}
