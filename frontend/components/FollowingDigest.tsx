"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { Bell, Dna, MapPin, Sparkles, TrendingUp } from "lucide-react";
import {
  DIGEST_WINDOWS,
  buildDigest,
  type DigestWindow,
  type EntityDigest
} from "@/lib/digest";
import { CATEGORY_META, type CategorizedEvent } from "@/lib/speciesEvents";
import type { ObserverFollowsData, ObserverNotificationsData, RegionSummary, SpeciesSummary } from "@/lib/types";

type FollowingDigestProps = {
  follows: ObserverFollowsData | null;
  notifications: ObserverNotificationsData | null;
  currentWorldAge: number;
};

export function FollowingDigest({ follows, notifications, currentWorldAge }: FollowingDigestProps) {
  const [windowKey, setWindowKey] = useState<DigestWindow["key"]>("day");
  const window = DIGEST_WINDOWS.find((item) => item.key === windowKey) ?? DIGEST_WINDOWS[0];
  const digest = useMemo(
    () => buildDigest(follows, notifications, window, currentWorldAge),
    [follows, notifications, window, currentWorldAge]
  );

  const hasFollows = digest.regions.length + digest.species.length > 0;

  return (
    <section className="following-digest" aria-label="Following digest">
      <header className="digest-head">
        <div>
          <p className="eyebrow">Engagement</p>
          <h2>Your Following Digest</h2>
        </div>
        <div className="digest-window" role="group" aria-label="Digest window">
          {DIGEST_WINDOWS.map((item) => (
            <button
              key={item.key}
              type="button"
              aria-pressed={item.key === windowKey}
              className={item.key === windowKey ? "active" : undefined}
              onClick={() => setWindowKey(item.key)}
            >
              {item.label}
            </button>
          ))}
        </div>
      </header>

      <div className="digest-summary">
        <DigestStat icon={<MapPin size={15} />} label="Regions" value={digest.summary.followedRegions} />
        <DigestStat icon={<Dna size={15} />} label="Species" value={digest.summary.followedSpecies} />
        <DigestStat icon={<Bell size={15} />} label="Unread" value={digest.summary.totalUnread} accent={digest.summary.totalUnread > 0} />
        <DigestStat icon={<TrendingUp size={15} />} label="Window events" value={digest.summary.windowEvents} />
        <DigestStat icon={<Sparkles size={15} />} label="Key moments" value={digest.summary.importantEvents} />
      </div>

      {!hasFollows ? (
        <div className="digest-empty">
          <Bell size={20} aria-hidden="true" />
          <h3>You are not following anything yet</h3>
          <p>
            Follow a <Link href="/universe">region</Link> or{" "}
            <Link href="/species/sp-0001">species</Link> to build a personal digest of Alpha&apos;s
            movement.
          </p>
        </div>
      ) : (
        <>
          {digest.highlights.length ? (
            <div className="digest-highlights">
              <h3>
                <Sparkles size={15} aria-hidden="true" /> Why come back
              </h3>
              <ul>
                {digest.highlights.map((item) => (
                  <HighlightRow key={item.event.id} item={item} />
                ))}
              </ul>
            </div>
          ) : (
            <p className="digest-quiet">
              No key moments in this window. Widen to {windowKey === "day" ? "Weekly" : "All time"}{" "}
              to see more.
            </p>
          )}

          <div className="digest-entity-grid">
            {digest.regions.map((entity) => (
              <EntityCard key={entity.follow.id} entity={entity} />
            ))}
            {digest.species.map((entity) => (
              <EntityCard key={entity.follow.id} entity={entity} />
            ))}
          </div>
        </>
      )}
    </section>
  );
}

function DigestStat({
  icon,
  label,
  value,
  accent = false
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  accent?: boolean;
}) {
  return (
    <div className={accent ? "digest-stat accent" : "digest-stat"}>
      <span className="digest-stat-icon" aria-hidden="true">
        {icon}
      </span>
      <span className="digest-stat-label">{label}</span>
      <strong>{value.toLocaleString()}</strong>
    </div>
  );
}

function HighlightRow({ item }: { item: CategorizedEvent }) {
  const meta = CATEGORY_META[item.category];
  const href = targetHref(item);
  const body = (
    <>
      <span className={`replay-event-badge tone-${meta.tone}`}>{meta.label}</span>
      <span className="highlight-body">
        <strong>{item.event.title}</strong>
        <small>
          Age {item.event.worldAge.toLocaleString()}
          {item.event.regionName || item.event.speciesName
            ? ` · ${item.event.speciesName ?? item.event.regionName}`
            : ""}
        </small>
      </span>
    </>
  );
  return (
    <li className={`highlight-row tone-${meta.tone}`}>
      {href ? <Link href={href}>{body}</Link> : <div className="highlight-static">{body}</div>}
    </li>
  );
}

function EntityCard({ entity }: { entity: EntityDigest }) {
  const isRegion = entity.entityType === "region";
  const href = `${isRegion ? "/regions" : "/species"}/${entity.follow.entityId}`;
  const name = entityName(entity);

  return (
    <article className="digest-entity-card">
      <header>
        <span className="entity-kind" aria-hidden="true">
          {isRegion ? <MapPin size={14} /> : <Dna size={14} />}
        </span>
        <Link href={href} className="entity-name">
          {name}
        </Link>
        {entity.unreadCount > 0 ? (
          <span className="entity-unread" aria-label={`${entity.unreadCount} unread`}>
            {entity.unreadCount}
          </span>
        ) : null}
      </header>

      <div className="entity-metrics">{entityMetrics(entity)}</div>

      {entity.categories.length ? (
        <div className="entity-categories">
          {entity.categories.map(({ category, count }) => {
            const meta = CATEGORY_META[category];
            return (
              <span className={`legend-chip tone-${meta.tone}`} key={category}>
                <i aria-hidden="true" />
                {meta.label}
                <strong>{count}</strong>
              </span>
            );
          })}
        </div>
      ) : (
        <p className="entity-quiet">No activity in this window.</p>
      )}

      {entity.headline ? (
        <p className="entity-headline">
          <strong>Latest:</strong> {entity.headline.event.title}
          <small> · Age {entity.headline.event.worldAge.toLocaleString()}</small>
        </p>
      ) : null}
    </article>
  );
}

function entityName(entity: EntityDigest): string {
  const value = entity.follow.entity;
  if (entity.entityType === "species") {
    return (value as SpeciesSummary).name ?? entity.follow.entityId;
  }
  return (value as RegionSummary).id ?? entity.follow.entityId;
}

function entityMetrics(entity: EntityDigest): React.ReactNode {
  if (entity.entityType === "region") {
    const region = entity.follow.entity as RegionSummary;
    return (
      <>
        <Metric label="Population" value={region.population.toLocaleString()} />
        <Metric label="Stability" value={`${Math.round(region.stability * 100)}%`} />
        <Metric
          label="State"
          value={region.collapsed ? "Collapsed" : "Active"}
          tone={region.collapsed ? "danger" : undefined}
        />
      </>
    );
  }
  const species = entity.follow.entity as SpeciesSummary;
  return (
    <>
      <Metric label="Population" value={species.population.toLocaleString()} />
      <Metric label="Status" value={species.status} />
      <Metric label="Gen" value={String(species.generation)} />
    </>
  );
}

function Metric({ label, value, tone }: { label: string; value: string; tone?: "danger" }) {
  return (
    <div className={tone === "danger" ? "entity-metric danger" : "entity-metric"}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function targetHref(item: CategorizedEvent): string | null {
  const event = item.event;
  if (event.speciesId) {
    return `/species/${event.speciesId}`;
  }
  if (event.regionId) {
    return `/regions/${event.regionId}`;
  }
  return null;
}
