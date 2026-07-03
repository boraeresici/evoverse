import Link from "next/link";
import { ArrowRight, CircleAlert, Dna, RadioTower, Waves } from "lucide-react";
import type { ChronicleEvent } from "@/lib/types";

type EventListProps = {
  events: ChronicleEvent[];
  compact?: boolean;
};

export function EventList({ events, compact = false }: EventListProps) {
  return (
    <div className={compact ? "event-list compact" : "event-list"}>
      {events.map((event) => (
        <article className={`event-card severity-${event.severity}`} key={event.id}>
          <div className="event-icon" aria-hidden="true">
            {iconForEvent(event.eventType)}
          </div>
          <div className="event-body">
            <div className="event-meta">
              <span>{event.eventLabel}</span>
              <span>Age {event.worldAge.toLocaleString()}</span>
            </div>
            <h3>{event.title}</h3>
            <p>{event.summary}</p>
            <div className="event-actions">
              {event.regionId ? (
                <Link href={`/regions/${event.regionId}`}>
                  Region <ArrowRight size={15} aria-hidden="true" />
                </Link>
              ) : null}
              {event.speciesId ? (
                <Link href={`/species/${event.speciesId}`}>
                  Species <ArrowRight size={15} aria-hidden="true" />
                </Link>
              ) : null}
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}

function iconForEvent(eventType: string) {
  if (eventType.includes("mutation") || eventType.includes("species")) {
    return <Dna size={18} />;
  }
  if (eventType.includes("collapse")) {
    return <CircleAlert size={18} />;
  }
  if (eventType.includes("resource")) {
    return <Waves size={18} />;
  }
  return <RadioTower size={18} />;
}
