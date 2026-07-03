"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Clock, History } from "lucide-react";
import { TimeScrubber } from "@/components/TimeScrubber";
import { UniverseExplorer } from "@/components/UniverseExplorer";
import {
  TIME_ZOOMS,
  eraForAge,
  snapshotRegionToSummary,
  snapshotSpeciesToSummary,
  speciesNameIndex,
  type TimeZoom
} from "@/lib/timeline";
import type {
  ChronicleEvent,
  RegionSummary,
  SnapshotAggregate,
  SnapshotDetails,
  SpeciesSummary
} from "@/lib/types";

const PLAY_INTERVAL_MS = 700;

type UniverseTimeExplorerProps = {
  liveRegions: RegionSummary[];
  liveSpecies: SpeciesSummary[];
  liveEvents: ChronicleEvent[];
  frames: SnapshotAggregate[];
};

type HistoricalFrame = {
  regions: RegionSummary[];
  species: SpeciesSummary[];
};

export function UniverseTimeExplorer({
  liveRegions,
  liveSpecies,
  liveEvents,
  frames
}: UniverseTimeExplorerProps) {
  // frames are passed newest-first from the snapshots API; present ascending.
  const ordered = useMemo(() => [...frames].sort((a, b) => a.worldAge - b.worldAge), [frames]);

  const [activeIndex, setActiveIndex] = useState<number | null>(null); // null = live
  const [playing, setPlaying] = useState(false);
  const [zoom, setZoom] = useState<TimeZoom>(TIME_ZOOMS[0]);
  const [logAxis, setLogAxis] = useState(false);
  const [historical, setHistorical] = useState<HistoricalFrame | null>(null);
  const [loading, setLoading] = useState(false);

  const cache = useRef<Map<number, HistoricalFrame>>(new Map());
  const fetchTimer = useRef<number | null>(null);
  const requestSeq = useRef(0);

  const live = activeIndex === null;
  const startIndex = useMemo(() => {
    if (ordered.length === 0) {
      return 0;
    }
    return Math.max(0, Math.floor(ordered.length * (1 - zoom.span)));
  }, [ordered.length, zoom.span]);

  const loadFrame = useCallback(
    async (tick: number): Promise<HistoricalFrame | null> => {
      const cached = cache.current.get(tick);
      if (cached) {
        return cached;
      }
      const response = await fetch(`/api/snapshots/${tick}/details`, {
        cache: "no-store"
      });
      if (!response.ok) {
        return null;
      }
      const data = (await response.json()) as SnapshotDetails;
      const nameById = speciesNameIndex(data.species);
      const frame: HistoricalFrame = {
        regions: data.regions.map((row) => snapshotRegionToSummary(row, nameById)),
        species: data.species.map(snapshotSpeciesToSummary)
      };
      cache.current.set(tick, frame);
      return frame;
    },
    []
  );

  // Debounced fetch of the selected historical frame.
  useEffect(() => {
    if (activeIndex === null) {
      setHistorical(null);
      setLoading(false);
      return;
    }
    const frame = ordered[activeIndex];
    if (!frame) {
      return;
    }
    const seq = (requestSeq.current += 1);
    const cached = cache.current.get(frame.tick);
    if (cached) {
      setHistorical(cached);
      setLoading(false);
      return;
    }
    setLoading(true);
    if (fetchTimer.current) {
      window.clearTimeout(fetchTimer.current);
    }
    fetchTimer.current = window.setTimeout(() => {
      void loadFrame(frame.tick).then((result) => {
        if (seq === requestSeq.current) {
          if (result) {
            setHistorical(result);
          }
          setLoading(false);
        }
      });
    }, 90);
    return () => {
      if (fetchTimer.current) {
        window.clearTimeout(fetchTimer.current);
      }
    };
  }, [activeIndex, ordered, loadFrame]);

  // Cinematic playback: advance through frames.
  useEffect(() => {
    if (!playing || ordered.length === 0) {
      return;
    }
    const timer = window.setInterval(() => {
      setActiveIndex((index) => {
        const from = index === null ? startIndex : index + 1;
        if (from >= ordered.length) {
          setPlaying(false);
          return null; // reached the present -> snap to live
        }
        return from;
      });
    }, PLAY_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [playing, ordered.length, startIndex]);

  const goLive = useCallback(() => {
    setPlaying(false);
    setActiveIndex(null);
  }, []);

  const seek = useCallback((index: number) => {
    setPlaying(false);
    setActiveIndex(index);
  }, []);

  const togglePlay = useCallback(() => {
    setPlaying((value) => {
      const next = !value;
      if (next && activeIndex === null) {
        setActiveIndex(startIndex);
      }
      return next;
    });
  }, [activeIndex, startIndex]);

  const activeFrame = activeIndex !== null ? ordered[activeIndex] : null;

  const showRegions = live ? liveRegions : historical?.regions ?? liveRegions;
  const showSpecies = live ? liveSpecies : historical?.species ?? liveSpecies;
  const showEvents = live ? liveEvents : [];

  if (ordered.length === 0) {
    // No snapshot history available: fall back to the live-only map.
    return <UniverseExplorer regions={liveRegions} species={liveSpecies} events={liveEvents} />;
  }

  return (
    <div className={`universe-time-explorer${live ? "" : " viewing-history"}`}>
      <TimeScrubber
        frames={ordered}
        startIndex={startIndex}
        activeIndex={activeIndex}
        live={live}
        playing={playing}
        loading={loading}
        zoom={zoom}
        logAxis={logAxis}
        onSeek={seek}
        onTogglePlay={togglePlay}
        onLive={goLive}
        onZoom={setZoom}
        onToggleLog={() => setLogAxis((value) => !value)}
      />

      {!live && activeFrame ? (
        <div className="history-banner" role="status">
          <History size={15} aria-hidden="true" />
          <span>
            Viewing Alpha history at <strong>Age {activeFrame.worldAge.toLocaleString()}</strong> ·{" "}
            {eraForAge(activeFrame.worldAge).label} Era ·{" "}
            {activeFrame.speciesCount.toLocaleString()} species ·{" "}
            {activeFrame.populationCount.toLocaleString()} population
          </span>
          <button type="button" onClick={goLive}>
            <Clock size={14} aria-hidden="true" />
            Return to now
          </button>
        </div>
      ) : null}

      <div className={live ? "time-map-frame" : "time-map-frame history"}>
        <UniverseExplorer regions={showRegions} species={showSpecies} events={showEvents} />
      </div>
    </div>
  );
}
