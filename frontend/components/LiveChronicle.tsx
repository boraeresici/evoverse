"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { EventList } from "@/components/EventList";
import type { ChronicleData, ChronicleEvent } from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
const MAX_EVENTS = 100;
const POLL_INTERVAL_MS = 10_000;

type StreamState = "connecting" | "live" | "reconnecting" | "polling";

type LiveChronicleProps = {
  initialEvents: ChronicleEvent[];
  filters?: ChronicleFilters;
  timeFilter: string;
};

type ChronicleFilters = {
  eventType?: string;
  minSeverity?: number;
  regionId?: string;
  speciesId?: string;
  query?: string;
};

export function LiveChronicle({ filters = {}, initialEvents, timeFilter }: LiveChronicleProps) {
  const [events, setEvents] = useState(initialEvents);
  const [streamState, setStreamState] = useState<StreamState>("connecting");
  const latestEventId = useRef(initialEvents[0]?.id ?? null);
  const visibleEvents = useMemo(() => applyFilters(events, filters), [events, filters]);

  useEffect(() => {
    setEvents(initialEvents);
    latestEventId.current = initialEvents[0]?.id ?? null;
  }, [initialEvents]);

  useEffect(() => {
    let closed = false;

    if (typeof EventSource === "undefined") {
      setStreamState("polling");
      const poll = async () => {
        const nextEvents = await fetchChronicle(timeFilter);
        if (closed || !nextEvents) {
          return;
        }
        latestEventId.current = nextEvents[0]?.id ?? latestEventId.current;
        setEvents(nextEvents);
      };
      void poll();
      const intervalId = window.setInterval(poll, POLL_INTERVAL_MS);
      return () => {
        closed = true;
        window.clearInterval(intervalId);
      };
    }

    const params = new URLSearchParams();
    if (latestEventId.current) {
      params.set("lastEventId", latestEventId.current);
    }
    const query = params.toString();
    const source = new EventSource(
      `${API_URL}/universes/alpha/events/stream${query ? `?${query}` : ""}`
    );

    source.addEventListener("stream_status", () => {
      if (!closed) {
        setStreamState("live");
      }
    });
    source.addEventListener("heartbeat", () => {
      if (!closed) {
        setStreamState("live");
      }
    });
    source.addEventListener("chronicle_event", (message) => {
      if (closed) {
        return;
      }
      const event = JSON.parse((message as MessageEvent).data) as ChronicleEvent;
      latestEventId.current = event.id;
      setStreamState("live");
      setEvents((current) => mergeEvent(event, current));
    });
    source.onerror = () => {
      if (!closed) {
        setStreamState("reconnecting");
      }
    };

    return () => {
      closed = true;
      source.close();
    };
  }, [timeFilter]);

  const streamLabel = useMemo(() => {
    if (streamState === "polling") {
      return "Polling";
    }
    if (streamState === "reconnecting") {
      return "Reconnecting";
    }
    if (streamState === "connecting") {
      return "Connecting";
    }
    return "Live";
  }, [streamState]);

  return (
    <section className="chronicle-live-panel">
      <div className="chronicle-live-bar" aria-live="polite">
        <span className={`live-indicator ${streamState}`} aria-hidden="true" />
        <span>{streamLabel}</span>
        <span>{visibleEvents.length.toLocaleString()} records</span>
      </div>
      <EventList events={visibleEvents} />
    </section>
  );
}

async function fetchChronicle(timeFilter: string): Promise<ChronicleEvent[] | null> {
  try {
    const response = await fetch(
      `${API_URL}/universes/alpha/chronicle?timeFilter=${encodeURIComponent(timeFilter)}`,
      { cache: "no-store" }
    );
    if (!response.ok) {
      return null;
    }
    const data = (await response.json()) as ChronicleData;
    return data.events;
  } catch {
    return null;
  }
}

function mergeEvent(nextEvent: ChronicleEvent, currentEvents: ChronicleEvent[]) {
  const seen = new Set<string>();
  return [nextEvent, ...currentEvents]
    .filter((event) => {
      if (seen.has(event.id)) {
        return false;
      }
      seen.add(event.id);
      return true;
    })
    .slice(0, MAX_EVENTS);
}

function applyFilters(events: ChronicleEvent[], filters: ChronicleFilters) {
  const query = filters.query?.trim().toLowerCase();
  return events.filter((event) => {
    if (filters.eventType && event.eventType !== filters.eventType) {
      return false;
    }
    if (filters.minSeverity && event.severity < filters.minSeverity) {
      return false;
    }
    if (filters.regionId && event.regionId !== filters.regionId) {
      return false;
    }
    if (filters.speciesId && event.speciesId !== filters.speciesId) {
      return false;
    }
    if (query) {
      return [event.title, event.summary, event.eventLabel]
        .join(" ")
        .toLowerCase()
        .includes(query);
    }
    return true;
  });
}
