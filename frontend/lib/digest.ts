import { categorizeEvent, type CategorizedEvent, type EventCategory } from "./speciesEvents";
import type { ObserverFollow, ObserverFollowsData, ObserverNotificationsData } from "./types";

// Placeholder cadence spans expressed in world-age units. The literal
// tick -> calendar mapping is still an open product decision, so "Daily" and
// "Weekly" are derived from a single tunable constant rather than hard dates.
const AGE_PER_DAY = 48;

export type DigestWindowKey = "day" | "week" | "all";

export type DigestWindow = {
  key: DigestWindowKey;
  label: string;
  spanWorldAge: number | null;
};

export const DIGEST_WINDOWS: DigestWindow[] = [
  { key: "day", label: "Daily", spanWorldAge: AGE_PER_DAY },
  { key: "week", label: "Weekly", spanWorldAge: AGE_PER_DAY * 7 },
  { key: "all", label: "All time", spanWorldAge: null }
];

export type EntityDigest = {
  follow: ObserverFollow;
  entityType: "region" | "species";
  unreadCount: number;
  windowCount: number;
  totalCount: number;
  lastActivityWorldAge: number | null;
  categories: Array<{ category: EventCategory; count: number }>;
  recent: CategorizedEvent[];
  headline: CategorizedEvent | null;
};

export type Digest = {
  window: DigestWindow;
  currentWorldAge: number;
  sinceWorldAge: number | null;
  summary: {
    followedRegions: number;
    followedSpecies: number;
    totalUnread: number;
    windowEvents: number;
    importantEvents: number;
  };
  highlights: CategorizedEvent[];
  regions: EntityDigest[];
  species: EntityDigest[];
};

type NotificationWithMeta = {
  categorized: CategorizedEvent;
  targetType: "region" | "species" | null;
  targetId: string | null;
  read: boolean;
  worldAge: number;
};

export function buildDigest(
  follows: ObserverFollowsData | null,
  notifications: ObserverNotificationsData | null,
  window: DigestWindow,
  currentWorldAgeHint = 0
): Digest {
  const rawNotifications = notifications?.notifications ?? [];
  const enriched: NotificationWithMeta[] = rawNotifications.map((notification) => ({
    categorized: categorizeEvent(notification.event),
    targetType: notification.target?.type ?? null,
    targetId: notification.target?.id ?? null,
    read: notification.read,
    worldAge: notification.event.worldAge
  }));

  const currentWorldAge = Math.max(
    currentWorldAgeHint,
    ...enriched.map((item) => item.worldAge),
    0
  );
  const sinceWorldAge = window.spanWorldAge === null ? null : currentWorldAge - window.spanWorldAge;
  const inWindow = (worldAge: number) => sinceWorldAge === null || worldAge >= sinceWorldAge;

  const regionDigests = (follows?.follows.regions ?? []).map((follow) =>
    buildEntityDigest(follow, "region", enriched, inWindow)
  );
  const speciesDigests = (follows?.follows.species ?? []).map((follow) =>
    buildEntityDigest(follow, "species", enriched, inWindow)
  );

  // Highlights: important events in-window across all follows, deduped by event.
  const seen = new Set<string>();
  const highlights = enriched
    .filter((item) => item.categorized.important && inWindow(item.worldAge))
    .sort((a, b) => b.worldAge - a.worldAge)
    .filter((item) => {
      if (seen.has(item.categorized.event.id)) {
        return false;
      }
      seen.add(item.categorized.event.id);
      return true;
    })
    .slice(0, 5)
    .map((item) => item.categorized);

  const windowEventIds = new Set(
    enriched.filter((item) => inWindow(item.worldAge)).map((item) => item.categorized.event.id)
  );
  const importantEventIds = new Set(
    enriched
      .filter((item) => item.categorized.important && inWindow(item.worldAge))
      .map((item) => item.categorized.event.id)
  );

  return {
    window,
    currentWorldAge,
    sinceWorldAge,
    summary: {
      followedRegions: regionDigests.length,
      followedSpecies: speciesDigests.length,
      totalUnread: notifications?.unreadCount ?? 0,
      windowEvents: windowEventIds.size,
      importantEvents: importantEventIds.size
    },
    highlights,
    regions: regionDigests,
    species: speciesDigests
  };
}

function buildEntityDigest(
  follow: ObserverFollow,
  entityType: "region" | "species",
  enriched: NotificationWithMeta[],
  inWindow: (worldAge: number) => boolean
): EntityDigest {
  const matching = enriched.filter(
    (item) => item.targetType === entityType && item.targetId === follow.entityId
  );
  const windowMatching = matching.filter((item) => inWindow(item.worldAge));

  const categoryCounts = new Map<EventCategory, number>();
  for (const item of windowMatching) {
    const category = item.categorized.category;
    categoryCounts.set(category, (categoryCounts.get(category) ?? 0) + 1);
  }

  const recent = windowMatching
    .slice()
    .sort((a, b) => b.worldAge - a.worldAge)
    .slice(0, 4)
    .map((item) => item.categorized);

  const headline =
    windowMatching
      .slice()
      .sort(
        (a, b) =>
          Number(b.categorized.important) - Number(a.categorized.important) ||
          b.worldAge - a.worldAge
      )[0]?.categorized ?? null;

  return {
    follow,
    entityType,
    unreadCount: matching.filter((item) => !item.read).length,
    windowCount: windowMatching.length,
    totalCount: matching.length,
    lastActivityWorldAge: matching.length
      ? Math.max(...matching.map((item) => item.worldAge))
      : null,
    categories: Array.from(categoryCounts.entries())
      .map(([category, count]) => ({ category, count }))
      .sort((a, b) => b.count - a.count),
    recent,
    headline
  };
}
