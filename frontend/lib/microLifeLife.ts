import type { MicroLifeAgent } from "./microLifeProjection";

export type LiveAgentState = "spawning" | "alive" | "dying";

export type LiveAgent = MicroLifeAgent & {
  life: number; // 0..1 render presence
  state: LiveAgentState;
};

// Births take ~0.45s to fade/scale in, deaths ~0.4s to fade out.
const SPAWN_RATE = 2.2;
const DIE_RATE = 2.5;

/**
 * Reconcile the persistent agent pool against a freshly built projection so
 * population changes read as real births and deaths instead of a re-seed.
 * Surviving agents keep their position and motion for continuity; only new ids
 * spawn and vanished ids begin dying.
 */
export function reconcileAgents(pool: Map<string, LiveAgent>, agents: MicroLifeAgent[]): void {
  const nextIds = new Set(agents.map((agent) => agent.id));

  for (const agent of agents) {
    const existing = pool.get(agent.id);
    if (!existing) {
      pool.set(agent.id, { ...agent, life: 0, state: "spawning" });
    } else if (existing.state === "dying") {
      // Reappeared before finishing its death: revive it.
      existing.state = existing.life >= 1 ? "alive" : "spawning";
    }
  }

  for (const [id, agent] of pool) {
    if (!nextIds.has(id) && agent.state !== "dying") {
      agent.state = "dying";
    }
  }
}

/** Integrate agent life by dt (seconds); remove agents whose death completed. */
export function advanceAgents(pool: Map<string, LiveAgent>, dt: number): void {
  for (const [id, agent] of pool) {
    if (agent.state === "dying") {
      agent.life -= dt * DIE_RATE;
      if (agent.life <= 0) {
        pool.delete(id);
      }
    } else if (agent.state === "spawning") {
      agent.life += dt * SPAWN_RATE;
      if (agent.life >= 1) {
        agent.life = 1;
        agent.state = "alive";
      }
    } else {
      agent.life = 1;
    }
  }
}

/** Snap the pool to its steady state (paused / reduced-motion rendering). */
export function settleAgents(pool: Map<string, LiveAgent>): void {
  for (const [id, agent] of pool) {
    if (agent.state === "dying") {
      pool.delete(id);
    } else {
      agent.life = 1;
      agent.state = "alive";
    }
  }
}

export function liveAgentList(pool: Map<string, LiveAgent>): LiveAgent[] {
  return [...pool.values()];
}

/** Smoothstep easing so spawns pop in and deaths ease out. */
export function easeLife(life: number): number {
  const l = Math.max(0, Math.min(1, life));
  return l * l * (3 - 2 * l);
}
