"use client";

import { useState } from "react";
import { Zap } from "lucide-react";

type CatalystActionsProps = {
  regionId: string;
  collapsed?: boolean;
};

const actions = [
  ["energy_pulse", "Energy Pulse"],
  ["mutation_pulse", "Mutation Pulse"],
  ["resource_burst", "Resource Burst"]
] as const;

export function CatalystActions({ regionId, collapsed = false }: CatalystActionsProps) {
  const [pending, setPending] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function submit(actionType: string) {
    setPending(actionType);
    setMessage(null);
    try {
      const response = await fetch("/api/catalyst/action", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ regionId, actionType })
      });
      if (!response.ok) {
        throw new Error("Catalyst action rejected");
      }
      setMessage("Influence initiated");
    } catch {
      setMessage("Catalyst link unavailable");
    } finally {
      setPending(null);
    }
  }

  if (collapsed) {
    return (
      <section className="catalyst-panel catalyst-panel-collapsed" aria-label="Catalyst actions">
        <div>
          <Zap size={17} aria-hidden="true" />
          <strong>Collapsed region protocol</strong>
          <span>
            Catalyst actions are paused here until recovery controls and rollback rules are
            formalized.
          </span>
        </div>
      </section>
    );
  }

  return (
    <section className="catalyst-panel" aria-label="Catalyst actions">
      {actions.map(([actionType, label]) => (
        <button
          disabled={pending !== null}
          key={actionType}
          onClick={() => submit(actionType)}
          type="button"
        >
          <Zap size={17} aria-hidden="true" />
          {pending === actionType ? "Initiating" : label}
        </button>
      ))}
      {message ? <span className="catalyst-message">{message}</span> : null}
    </section>
  );
}
