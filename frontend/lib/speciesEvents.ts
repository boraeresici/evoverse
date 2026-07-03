import type { ChronicleEvent } from "./types";

export type EventCategory =
  | "emergence"
  | "major_mutation"
  | "mutation"
  | "extinction"
  | "decline"
  | "collapse"
  | "resource_shift"
  | "catalyst"
  | "other";

export type EventTone =
  | "emergence"
  | "mutation"
  | "decline"
  | "collapse"
  | "catalyst"
  | "neutral";

export type CategorizedEvent = {
  event: ChronicleEvent;
  category: EventCategory;
  tone: EventTone;
  label: string;
  important: boolean;
};

export const CATEGORY_META: Record<
  EventCategory,
  { label: string; tone: EventTone; short: string }
> = {
  emergence: { label: "Emergence", tone: "emergence", short: "New" },
  major_mutation: { label: "Major mutation", tone: "mutation", short: "Mut+" },
  mutation: { label: "Mutation", tone: "mutation", short: "Mut" },
  extinction: { label: "Extinction", tone: "decline", short: "Ext" },
  decline: { label: "Decline", tone: "decline", short: "Dec" },
  collapse: { label: "Region collapse", tone: "collapse", short: "Col" },
  resource_shift: { label: "Resource shift", tone: "neutral", short: "Res" },
  catalyst: { label: "Catalyst", tone: "catalyst", short: "Cat" },
  other: { label: "Signal", tone: "neutral", short: "Sig" }
};

// A mutation counts as "major" once its largest trait delta crosses this bound.
const MAJOR_MUTATION_DELTA = 0.08;
// A decline that erases this share of the population reads as an extinction moment.
const EXTINCTION_DECLINE_PERCENT = 55;

export function maxTraitDelta(payload: ChronicleEvent["payload"]): number {
  const deltas = payload?.trait_deltas;
  if (deltas && typeof deltas === "object" && !Array.isArray(deltas)) {
    const values = Object.values(deltas as Record<string, unknown>).map((value) =>
      Math.abs(Number(value) || 0)
    );
    return values.length ? Math.max(...values) : 0;
  }
  return 0;
}

export function declinePercent(payload: ChronicleEvent["payload"]): number {
  const value = payload?.decline_percent;
  return Number(value) || 0;
}

export function categorizeEvent(
  event: ChronicleEvent,
  options: { extinctLineage?: boolean } = {}
): CategorizedEvent {
  const type = event.eventType;

  if (type.includes("species_emerged")) {
    return build(event, "emergence");
  }
  if (type.includes("mutation_detected")) {
    const major = maxTraitDelta(event.payload) >= MAJOR_MUTATION_DELTA || event.severity >= 4;
    return build(event, major ? "major_mutation" : "mutation");
  }
  if (type.includes("species_declined")) {
    const percent = declinePercent(event.payload);
    const extinction = options.extinctLineage || percent >= EXTINCTION_DECLINE_PERCENT;
    return build(event, extinction ? "extinction" : "decline");
  }
  if (type.includes("region_collapse")) {
    return build(event, "collapse");
  }
  if (type.includes("region_resource_shift")) {
    return build(event, "resource_shift");
  }
  if (type.includes("catalyst")) {
    return build(event, "catalyst");
  }
  return build(event, "other");
}

const IMPORTANT_CATEGORIES: ReadonlySet<EventCategory> = new Set([
  "emergence",
  "major_mutation",
  "extinction",
  "collapse"
]);

function build(event: ChronicleEvent, category: EventCategory): CategorizedEvent {
  const meta = CATEGORY_META[category];
  return {
    event,
    category,
    tone: meta.tone,
    label: meta.label,
    important: IMPORTANT_CATEGORIES.has(category)
  };
}

export function categorizeTimeline(
  events: ChronicleEvent[],
  options: { extinctLineage?: boolean } = {}
): CategorizedEvent[] {
  const categorized = events.map((event) => categorizeEvent(event, options));
  if (options.extinctLineage) {
    // Only the last decline in an extinct lineage is the true extinction moment.
    const declineIndexes = categorized
      .map((item, index) => ({ item, index }))
      .filter(({ item }) => item.category === "extinction" || item.category === "decline");
    declineIndexes.forEach(({ index }, order) => {
      if (order < declineIndexes.length - 1 && categorized[index].category === "extinction") {
        categorized[index] = build(categorized[index].event, "decline");
      }
    });
  }
  return categorized;
}

export function summarizeCategories(
  events: CategorizedEvent[]
): Array<{ category: EventCategory; count: number }> {
  const counts = new Map<EventCategory, number>();
  for (const item of events) {
    counts.set(item.category, (counts.get(item.category) ?? 0) + 1);
  }
  return Array.from(counts.entries())
    .map(([category, count]) => ({ category, count }))
    .sort((a, b) => b.count - a.count);
}
