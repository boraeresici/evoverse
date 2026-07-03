import { EmptyState } from "@/components/EmptyState";
import { FollowingDigest } from "@/components/FollowingDigest";
import { NotificationsPanel } from "@/components/NotificationsPanel";
import { getLanding, getObserverFollows, getObserverNotifications } from "@/lib/api";

export default async function NotificationsPage() {
  const [data, follows, landing] = await Promise.all([
    getObserverNotifications({ limit: 100 }),
    getObserverFollows(),
    getLanding()
  ]);

  if (!data) {
    return <EmptyState title="Notifications unavailable" />;
  }

  return (
    <main className="page-shell">
      <section className="page-title">
        <p className="eyebrow">Observer</p>
        <h1>Notifications</h1>
      </section>

      <FollowingDigest
        follows={follows}
        notifications={data}
        currentWorldAge={landing?.universe.ageYears ?? 0}
      />

      <section className="content-band flat">
        <div className="section-heading compact-heading">
          <div>
            <p className="eyebrow">Inbox</p>
            <h2>All Notifications</h2>
          </div>
        </div>
        <NotificationsPanel initialData={data} />
      </section>
    </main>
  );
}
