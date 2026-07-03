"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { Bell, Check, CheckCheck, CircleAlert, Dna, Loader2, MapPin, RadioTower } from "lucide-react";
import { CATEGORY_META, categorizeEvent, type EventCategory } from "@/lib/speciesEvents";
import type { ObserverNotification, ObserverNotificationsData } from "@/lib/types";

type NotificationsPanelProps = {
  initialData: ObserverNotificationsData;
};

type Decorated = ObserverNotification & {
  category: EventCategory;
  tone: string;
  categoryLabel: string;
};

export function NotificationsPanel({ initialData }: NotificationsPanelProps) {
  const [notifications, setNotifications] = useState(initialData.notifications);
  const [unreadCount, setUnreadCount] = useState(initialData.unreadCount);
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [markingAll, setMarkingAll] = useState(false);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [categoryFilter, setCategoryFilter] = useState<EventCategory | "all">("all");

  const decorated: Decorated[] = useMemo(
    () =>
      notifications.map((notification) => {
        const categorized = categorizeEvent(notification.event);
        return {
          ...notification,
          category: categorized.category,
          tone: categorized.tone,
          categoryLabel: categorized.label
        };
      }),
    [notifications]
  );

  const availableCategories = useMemo(() => {
    const counts = new Map<EventCategory, number>();
    for (const item of decorated) {
      counts.set(item.category, (counts.get(item.category) ?? 0) + 1);
    }
    return Array.from(counts.entries()).sort((a, b) => b[1] - a[1]);
  }, [decorated]);

  const visible = decorated.filter((item) => {
    if (unreadOnly && item.read) {
      return false;
    }
    if (categoryFilter !== "all" && item.category !== categoryFilter) {
      return false;
    }
    return true;
  });

  async function markRead(notification: ObserverNotification) {
    if (notification.read) {
      return;
    }
    setPendingId(notification.id);
    try {
      const response = await fetch("/api/observer/notifications/read", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ notificationId: notification.id })
      });
      if (!response.ok) {
        throw new Error("Notification read request failed");
      }
      setNotifications((current) =>
        current.map((item) => (item.id === notification.id ? { ...item, read: true } : item))
      );
      setUnreadCount((current) => Math.max(0, current - 1));
    } finally {
      setPendingId(null);
    }
  }

  async function markAllRead() {
    if (unreadCount === 0) {
      return;
    }
    setMarkingAll(true);
    try {
      const response = await fetch("/api/observer/notifications/read-all", { method: "POST" });
      if (!response.ok) {
        throw new Error("Mark all read failed");
      }
      setNotifications((current) => current.map((item) => ({ ...item, read: true })));
      setUnreadCount(0);
    } finally {
      setMarkingAll(false);
    }
  }

  return (
    <section className="notifications-panel">
      <div className="notification-stats">
        <Metric label="Unread" value={unreadCount.toLocaleString()} />
        <Metric label="Total" value={initialData.pagination.total.toLocaleString()} />
        <Metric label="Observer" value={initialData.user.id} />
      </div>

      <div className="notification-controls">
        <div className="notification-filters" role="group" aria-label="Notification filters">
          <button
            type="button"
            aria-pressed={!unreadOnly}
            className={!unreadOnly ? "active" : undefined}
            onClick={() => setUnreadOnly(false)}
          >
            All
          </button>
          <button
            type="button"
            aria-pressed={unreadOnly}
            className={unreadOnly ? "active" : undefined}
            onClick={() => setUnreadOnly(true)}
          >
            Unread
          </button>
        </div>
        <button
          type="button"
          className="notification-mark-all"
          disabled={unreadCount === 0 || markingAll}
          onClick={() => void markAllRead()}
        >
          {markingAll ? (
            <Loader2 size={15} aria-hidden="true" className="spin" />
          ) : (
            <CheckCheck size={15} aria-hidden="true" />
          )}
          Mark all read
        </button>
      </div>

      {availableCategories.length > 1 ? (
        <div className="notification-category-filter" role="group" aria-label="Category filter">
          <button
            type="button"
            aria-pressed={categoryFilter === "all"}
            className={`legend-chip${categoryFilter === "all" ? " active" : ""}`}
            onClick={() => setCategoryFilter("all")}
          >
            All
            <strong>{decorated.length}</strong>
          </button>
          {availableCategories.map(([category, count]) => {
            const meta = CATEGORY_META[category];
            return (
              <button
                type="button"
                key={category}
                aria-pressed={categoryFilter === category}
                className={`legend-chip tone-${meta.tone}${categoryFilter === category ? " active" : ""}`}
                onClick={() => setCategoryFilter(category)}
              >
                <i aria-hidden="true" />
                {meta.label}
                <strong>{count}</strong>
              </button>
            );
          })}
        </div>
      ) : null}

      {visible.length ? (
        <div className="notification-list">
          {visible.map((notification) => {
            const Icon = iconForNotification(notification.kind);
            return (
              <article
                className={`notification-item tone-${notification.tone}${notification.read ? " read" : ""}`}
                key={notification.id}
              >
                <div className="notification-icon" aria-hidden="true">
                  <Icon size={18} />
                </div>
                <div className="notification-body">
                  <div className="notification-meta">
                    <span className={`notification-category tone-${notification.tone}`}>
                      {notification.categoryLabel}
                    </span>
                    <span>{labelForNotification(notification.kind)}</span>
                    <span>Age {notification.event.worldAge.toLocaleString()}</span>
                    <span>{notification.read ? "Read" : "Unread"}</span>
                  </div>
                  <h2>{notification.title}</h2>
                  <p>{notification.summary}</p>
                  <div className="notification-actions">
                    {targetHref(notification) ? (
                      <Link href={targetHref(notification) ?? "#"}>{notification.target?.label}</Link>
                    ) : null}
                    <button
                      disabled={notification.read || pendingId === notification.id}
                      onClick={() => void markRead(notification)}
                      type="button"
                    >
                      <Check size={15} aria-hidden="true" />
                      {pendingId === notification.id
                        ? "Marking"
                        : notification.read
                          ? "Read"
                          : "Mark read"}
                    </button>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      ) : (
        <div className="notification-empty">
          <Bell size={22} aria-hidden="true" />
          <h2>{notifications.length ? "Nothing matches this filter" : "No notifications"}</h2>
          <p>{notifications.length ? "Try a different filter." : "All clear."}</p>
        </div>
      )}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="notification-stat">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function targetHref(notification: ObserverNotification) {
  if (!notification.target) {
    return null;
  }
  return notification.target.type === "region"
    ? `/regions/${notification.target.id}`
    : `/species/${notification.target.id}`;
}

function labelForNotification(kind: ObserverNotification["kind"]) {
  if (kind === "followed_region_event") {
    return "Region";
  }
  if (kind === "followed_species_event") {
    return "Species";
  }
  if (kind === "catalyst_downstream_event") {
    return "Catalyst result";
  }
  return "Catalyst";
}

function iconForNotification(kind: ObserverNotification["kind"]) {
  if (kind === "followed_species_event") {
    return Dna;
  }
  if (kind === "followed_region_event") {
    return MapPin;
  }
  if (kind === "catalyst_downstream_event") {
    return CircleAlert;
  }
  return RadioTower;
}
