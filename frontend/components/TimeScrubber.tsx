"use client";

import { useCallback, useRef } from "react";
import { Loader2, Pause, Play, Radio } from "lucide-react";
import { ERA_BANDS, TIME_ZOOMS, axisPosition, frameSubtitle, type TimeZoom } from "@/lib/timeline";
import type { SnapshotAggregate } from "@/lib/types";

const VIEW_W = 1000;
const VIEW_H = 120;

type TimeScrubberProps = {
  frames: SnapshotAggregate[];
  startIndex: number;
  activeIndex: number | null;
  live: boolean;
  playing: boolean;
  loading: boolean;
  zoom: TimeZoom;
  logAxis: boolean;
  onSeek: (globalIndex: number) => void;
  onTogglePlay: () => void;
  onLive: () => void;
  onZoom: (zoom: TimeZoom) => void;
  onToggleLog: () => void;
};

export function TimeScrubber({
  frames,
  startIndex,
  activeIndex,
  live,
  playing,
  loading,
  zoom,
  logAxis,
  onSeek,
  onTogglePlay,
  onLive,
  onZoom,
  onToggleLog
}: TimeScrubberProps) {
  const trackRef = useRef<HTMLDivElement | null>(null);
  const dragging = useRef(false);

  const visible = frames.slice(startIndex);
  const minAge = visible[0]?.worldAge ?? 0;
  const maxAge = visible[visible.length - 1]?.worldAge ?? minAge + 1;

  const currentIndex = activeIndex ?? frames.length - 1;
  const currentFrame = frames[currentIndex] ?? frames[frames.length - 1] ?? null;

  const seekFromClientX = useCallback(
    (clientX: number) => {
      const track = trackRef.current;
      if (!track || visible.length === 0) {
        return;
      }
      const rect = track.getBoundingClientRect();
      const fraction = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
      const targetAge = minAge + fraction * (maxAge - minAge);
      // Nearest visible frame by world age.
      let best = 0;
      let bestDist = Infinity;
      for (let i = 0; i < visible.length; i += 1) {
        const dist = Math.abs(visible[i].worldAge - targetAge);
        if (dist < bestDist) {
          bestDist = dist;
          best = i;
        }
      }
      onSeek(startIndex + best);
    },
    [maxAge, minAge, onSeek, startIndex, visible]
  );

  const sparkline = buildSparkline(visible, minAge, maxAge, logAxis);
  const eraSegments = buildEraSegments(minAge, maxAge);
  const handleX = currentFrame
    ? axisPosition(currentFrame.worldAge, minAge, maxAge, logAxis) * VIEW_W
    : VIEW_W;

  return (
    <section className="time-scrubber" aria-label="Time navigation">
      <div className="scrubber-head">
        <div className="scrubber-caption">
          <span className={`scrubber-live-dot${live ? " live" : " history"}`} aria-hidden="true" />
          <strong>{live ? "Live" : "Time travel"}</strong>
          {currentFrame ? <span>{frameSubtitle(currentFrame)}</span> : null}
          {loading ? <Loader2 size={14} className="spin" aria-hidden="true" /> : null}
        </div>
        <div className="scrubber-eras" aria-hidden="true">
          {ERA_BANDS.filter((band) => band.minAge <= maxAge && band.maxAge > minAge).map((band) => (
            <span className={`era-key tone-era-${band.key}`} key={band.key}>
              <i />
              {band.label}
            </span>
          ))}
        </div>
      </div>

      <div
        className="scrubber-track"
        ref={trackRef}
        role="slider"
        tabIndex={0}
        aria-label="Alpha age scrubber"
        aria-valuemin={minAge}
        aria-valuemax={maxAge}
        aria-valuenow={currentFrame?.worldAge ?? maxAge}
        onPointerDown={(event) => {
          dragging.current = true;
          event.currentTarget.setPointerCapture(event.pointerId);
          seekFromClientX(event.clientX);
        }}
        onPointerMove={(event) => {
          if (dragging.current) {
            seekFromClientX(event.clientX);
          }
        }}
        onPointerUp={(event) => {
          dragging.current = false;
          event.currentTarget.releasePointerCapture(event.pointerId);
        }}
        onKeyDown={(event) => {
          if (event.key === "ArrowLeft") {
            event.preventDefault();
            onSeek(Math.max(startIndex, currentIndex - 1));
          } else if (event.key === "ArrowRight") {
            event.preventDefault();
            onSeek(Math.min(frames.length - 1, currentIndex + 1));
          }
        }}
      >
        <svg viewBox={`0 0 ${VIEW_W} ${VIEW_H}`} preserveAspectRatio="none" className="scrubber-svg">
          {eraSegments.map((seg) => (
            <rect
              key={seg.key}
              className={`era-band tone-era-${seg.key}`}
              x={seg.x}
              y={0}
              width={seg.width}
              height={VIEW_H}
            />
          ))}
          <polyline className="scrubber-spark" fill="none" points={sparkline.line} />
          <polyline className="scrubber-spark-fill" points={sparkline.fill} />
          <line className="scrubber-handle-line" x1={handleX} x2={handleX} y1={0} y2={VIEW_H} />
          <circle className="scrubber-handle-dot" cx={handleX} cy={VIEW_H / 2} r={7} />
        </svg>
      </div>

      <div className="scrubber-controls">
        <button type="button" className="scrubber-play" onClick={onTogglePlay} aria-label={playing ? "Pause" : "Play"}>
          {playing ? <Pause size={16} aria-hidden="true" /> : <Play size={16} aria-hidden="true" />}
          {playing ? "Pause" : "Play history"}
        </button>
        <button
          type="button"
          className={live ? "scrubber-live active" : "scrubber-live"}
          onClick={onLive}
          disabled={live}
        >
          <Radio size={15} aria-hidden="true" />
          Live
        </button>

        <div className="scrubber-zooms" role="group" aria-label="Time zoom">
          {TIME_ZOOMS.map((item) => (
            <button
              key={item.key}
              type="button"
              aria-pressed={item.key === zoom.key}
              className={item.key === zoom.key ? "active" : undefined}
              onClick={() => onZoom(item)}
            >
              {item.label}
            </button>
          ))}
        </div>

        <button
          type="button"
          className={logAxis ? "scrubber-log active" : "scrubber-log"}
          aria-pressed={logAxis}
          onClick={onToggleLog}
          title="Logarithmic time axis keeps early eras from being crushed"
        >
          Log axis
        </button>
      </div>
    </section>
  );
}

function buildSparkline(
  frames: SnapshotAggregate[],
  minAge: number,
  maxAge: number,
  logAxis: boolean
): { line: string; fill: string } {
  if (frames.length === 0) {
    return { line: "", fill: "" };
  }
  const values = frames.map((frame) => frame.populationCount);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const top = 12;
  const height = VIEW_H - 24;
  const points = frames.map((frame) => {
    const x = axisPosition(frame.worldAge, minAge, maxAge, logAxis) * VIEW_W;
    const y = top + height - ((frame.populationCount - min) / range) * height;
    return `${round(x)},${round(y)}`;
  });
  const fill = `0,${VIEW_H} ${points.join(" ")} ${VIEW_W},${VIEW_H}`;
  return { line: points.join(" "), fill };
}

function buildEraSegments(minAge: number, maxAge: number) {
  const segments: Array<{ key: string; x: number; width: number }> = [];
  for (const band of ERA_BANDS) {
    const segStart = Math.max(band.minAge, minAge);
    const segEnd = Math.min(band.maxAge, maxAge);
    if (segEnd <= segStart) {
      continue;
    }
    const x = ((segStart - minAge) / (maxAge - minAge || 1)) * VIEW_W;
    const width = ((segEnd - segStart) / (maxAge - minAge || 1)) * VIEW_W;
    segments.push({ key: band.key, x: round(x), width: round(width) });
  }
  return segments;
}

function round(value: number): number {
  return Math.round(value * 100) / 100;
}
