"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { EventList } from "@/components/EventList";
import type { ChronicleEvent } from "@/lib/types";

// The region payload already carries the full window of events, so "show more" is
// a pure client reveal — no extra fetch. We render a short head by default so the
// timeline doesn't run the page to several thousand pixels on busy regions.
const INITIAL_COUNT = 8;

type RegionTimelineProps = {
  events: ChronicleEvent[];
};

export function RegionTimeline({ events }: RegionTimelineProps) {
  const [expanded, setExpanded] = useState(false);
  const hasOverflow = events.length > INITIAL_COUNT;
  const visible = expanded ? events : events.slice(0, INITIAL_COUNT);

  return (
    <>
      <EventList events={visible} />
      {hasOverflow ? (
        <button
          className="event-list-toggle"
          onClick={() => setExpanded((value) => !value)}
          type="button"
          aria-expanded={expanded}
        >
          <ChevronDown
            className={expanded ? "toggle-caret open" : "toggle-caret"}
            size={16}
            aria-hidden="true"
          />
          {expanded
            ? "Show fewer events"
            : `Show all ${events.length.toLocaleString()} events`}
        </button>
      ) : null}
    </>
  );
}
