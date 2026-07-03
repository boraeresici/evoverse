import type { ChronicleEvent, RegionSummary, SpeciesSummary } from "@/lib/types";

type ChronicleFiltersProps = {
  events: ChronicleEvent[];
  regions: RegionSummary[];
  species: SpeciesSummary[];
  selected: {
    eventType?: string;
    minSeverity?: string;
    regionId?: string;
    speciesId?: string;
    query?: string;
    timeFilter: string;
  };
};

export function ChronicleFilters({
  events,
  regions,
  selected,
  species
}: ChronicleFiltersProps) {
  const eventTypes = Array.from(new Set(events.map((event) => event.eventType))).sort();

  return (
    <form action="/chronicle" className="chronicle-filter-panel">
      <input name="timeFilter" type="hidden" value={selected.timeFilter} />
      <label>
        <span>Event</span>
        <select name="eventType" defaultValue={selected.eventType ?? ""}>
          <option value="">All events</option>
          {eventTypes.map((eventType) => (
            <option key={eventType} value={eventType}>
              {eventType.replaceAll("_", " ")}
            </option>
          ))}
        </select>
      </label>
      <label>
        <span>Severity</span>
        <select name="minSeverity" defaultValue={selected.minSeverity ?? ""}>
          <option value="">Any</option>
          {[2, 3, 4, 5].map((severity) => (
            <option key={severity} value={severity}>
              {severity}+
            </option>
          ))}
        </select>
      </label>
      <label>
        <span>Region</span>
        <select name="regionId" defaultValue={selected.regionId ?? ""}>
          <option value="">All regions</option>
          {regions.map((region) => (
            <option key={region.id} value={region.id}>
              {region.id}
            </option>
          ))}
        </select>
      </label>
      <label>
        <span>Species</span>
        <select name="speciesId" defaultValue={selected.speciesId ?? ""}>
          <option value="">All species</option>
          {species.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        <span>Search</span>
        <input name="query" placeholder="Title or summary" defaultValue={selected.query ?? ""} />
      </label>
      <button className="primary-action chronicle-filter-apply" type="submit">
        Apply
      </button>
    </form>
  );
}
