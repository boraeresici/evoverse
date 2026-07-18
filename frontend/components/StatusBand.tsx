import { Activity, Clock3, Dna, Gauge, Map } from "lucide-react";
import { InfoTip } from "@/components/InfoTip";
import type { UniverseStatus } from "@/lib/types";

type StatusBandProps = {
  universe: UniverseStatus;
};

export function StatusBand({ universe }: StatusBandProps) {
  const metrics = [
    {
      label: "Alpha Age",
      value: `${universe.ageYears.toLocaleString()} years`,
      icon: Clock3,
      tip: "In-world time counter, not a wall-clock date. The tick-to-calendar mapping is an open product decision."
    },
    {
      label: "Era",
      value: universe.currentEra,
      icon: Activity,
      tip: "The universe's current developmental phase. Genesis → Expansion → Stabilization are reachable today; Intelligence is a designed future tier that has not shipped, so it is earned, not granted."
    },
    { label: "Active Species", value: universe.activeSpecies.toLocaleString(), icon: Dna },
    { label: "Regions", value: universe.regionCount.toLocaleString(), icon: Map },
    {
      label: "Stability",
      value: `${Math.round(universe.stabilityIndex * 100)}%`,
      icon: Gauge,
      tip: "Global mean of region stability. Higher means fewer collapses and calmer drift across Alpha."
    }
  ];

  return (
    <section className="status-band" aria-label="Alpha status">
      {metrics.map((metric) => {
        const Icon = metric.icon;
        return (
          <div className="status-metric" key={metric.label}>
            <Icon size={18} aria-hidden="true" />
            <span>
              {metric.label}
              {metric.tip ? <InfoTip text={metric.tip} label={metric.label} /> : null}
            </span>
            <strong>{metric.value}</strong>
          </div>
        );
      })}
    </section>
  );
}
