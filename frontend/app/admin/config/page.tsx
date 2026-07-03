import {
  Activity,
  AlertTriangle,
  CircleCheck,
  Database,
  KeyRound,
  Lock,
  Pencil,
  Radio,
  ShieldCheck,
  Unlock
} from "lucide-react";
import { EmptyState } from "@/components/EmptyState";
import { RulesEditor } from "@/components/RulesEditor";
import {
  getAdminRules,
  getAdminRulesAudit,
  getAdminRulesRevisions,
  getIdentityContext,
  getSimulationHealth
} from "@/lib/api";
import type { IdentityContextData, SimulationHealthData } from "@/lib/types";

export default async function AdminConfigPage() {
  const [data, identity, auditPage, revisionPage, health] = await Promise.all([
    getAdminRules(),
    getIdentityContext(),
    getAdminRulesAudit(),
    getAdminRulesRevisions(),
    getSimulationHealth()
  ]);

  if (!data) {
    return <EmptyState title="Simulation rules are unavailable" />;
  }

  const canApply = identity?.capabilities.admin.canUseAdmin ?? false;
  const gateReason = identity?.capabilities.admin.reason ?? null;

  return (
    <main className="page-shell admin-page">
      <section className="admin-hero">
        <div>
          <p className="eyebrow">Admin Config</p>
          <h1>Simulation Rules</h1>
        </div>
        <div className="admin-meta" aria-label="Rules metadata">
          <span>
            <Pencil size={16} aria-hidden="true" />
            {formatToken(data.mode)}
          </span>
          <span>
            <Database size={16} aria-hidden="true" />
            {data.model}
          </span>
          <span>
            <Activity size={16} aria-hidden="true" />
            {data.source}
          </span>
        </div>
      </section>

      {identity ? <IdentityGatePanel identity={identity} /> : null}

      {canApply ? (
        <>
          {health ? <OperationsPanel health={health} /> : null}
          <RulesEditor
            initialRules={data.rules}
            initialRevision={data.revision ?? 0}
            initialRulesHash={data.rulesHash ?? ""}
            initialAudit={auditPage?.audit ?? []}
            initialRevisions={revisionPage?.revisions ?? []}
            reloadStrategy={data.governance?.reloadStrategy ?? null}
            canApply={canApply}
            gateReason={gateReason}
          />
        </>
      ) : (
        <AdminGatePanel reason={gateReason} provider={identity?.auth.provider ?? "local"} />
      )}
    </main>
  );
}

function IdentityGatePanel({ identity }: { identity: IdentityContextData }) {
  const catalystPermission = identity.capabilities.catalyst.permission;
  const adminPermission = identity.capabilities.admin;

  return (
    <section className="identity-gate-panel" aria-label="Local identity and role gate">
      <header>
        <div>
          <p className="eyebrow">Identity Gate</p>
          <h2>Local Alpha Roles</h2>
        </div>
        <span>
          <KeyRound size={16} aria-hidden="true" />
          {formatToken(identity.auth.provider)} / {formatToken(identity.auth.status)}
        </span>
      </header>
      <div className="identity-role-grid">
        <IdentityRoleCard
          label="Auth"
          status={
            identity.auth.trustedHeaderRequired
              ? "Trusted header required"
              : identity.auth.localFallback
                ? "Local fallback on"
                : "Session required"
          }
          user={formatToken(identity.auth.provider)}
          value={`${formatToken(identity.auth.sessionStrategy)} / ${
            identity.auth.googleClientConfigured ? "Google client configured" : "Google client pending"
          }`}
        />
        <IdentityRoleCard
          label="Observer"
          status={identity.capabilities.observer.canFollow ? "Follow enabled" : "Follow gated"}
          user={identity.users.observer.id}
          value={formatToken(identity.roleGate.observerAccess)}
        />
        <IdentityRoleCard
          label="Catalyst"
          status={
            catalystPermission.canUseCatalyst
              ? "Influence enabled"
              : formatToken(catalystPermission.reason ?? "role required")
          }
          user={identity.users.catalyst.id}
          value={`${formatToken(identity.users.catalyst.role)} / ${formatToken(identity.users.catalyst.status)}`}
        />
        <IdentityRoleCard
          label="Admin"
          status={
            adminPermission.canUseAdmin
              ? "Admin enabled"
              : formatToken(adminPermission.reason ?? "role required")
          }
          user={identity.users.admin.id}
          value={`${formatToken(identity.users.admin.role)} / ${formatToken(identity.users.admin.status)}`}
        />
      </div>
    </section>
  );
}

function IdentityRoleCard({
  label,
  status,
  user,
  value
}: {
  label: string;
  status: string;
  user: string;
  value: string;
}) {
  return (
    <article className="identity-role-card">
      <ShieldCheck size={18} aria-hidden="true" />
      <span>{label}</span>
      <strong>{user}</strong>
      <small>{value}</small>
      <em>{status}</em>
    </article>
  );
}

function AdminGatePanel({ reason, provider }: { reason: string | null; provider: string }) {
  return (
    <section className="admin-gate-panel" aria-label="Admin access restricted">
      <Lock size={26} aria-hidden="true" />
      <h2>Admin access required</h2>
      <p>
        Simulation rules and operations controls are restricted to admin accounts. Your current
        identity does not have the admin role
        {reason ? ` (${formatToken(reason)})` : ""}.
      </p>
      <p className="admin-gate-hint">
        Provider: <strong>{formatToken(provider)}</strong>. Sign in with an admin account through the{" "}
        <a href="/auth">Access Console</a> to draft, apply, or roll back rules.
      </p>
    </section>
  );
}

function OperationsPanel({ health }: { health: SimulationHealthData }) {
  const ops = health.operations;
  const worker = health.worker;
  const stateTone =
    ops.workerState === "healthy"
      ? "ok"
      : ops.workerState === "stale" || ops.workerState === "error"
        ? "danger"
        : "warn";

  return (
    <section className="operations-panel" aria-label="Operations and worker health">
      <header>
        <div>
          <p className="eyebrow">Operations</p>
          <h2>Runtime &amp; Worker Health</h2>
        </div>
        <span className={`ops-env env-${ops.env}`}>
          <Radio size={15} aria-hidden="true" />
          {formatToken(ops.env)}
        </span>
      </header>

      <div className="ops-grid">
        <article className={`ops-card tone-${stateTone}`}>
          <span className="ops-card-label">Worker</span>
          <strong>{formatToken(ops.workerState)}</strong>
          <small>
            {health.workerStaleSeconds === null
              ? "No heartbeat recorded"
              : `Last beat ${Math.round(health.workerStaleSeconds)}s ago · threshold ${ops.workerStaleThresholdSeconds}s`}
          </small>
        </article>

        <article className="ops-card">
          <span className="ops-card-label">Simulation</span>
          <strong>Tick {health.tick.toLocaleString()}</strong>
          <small>
            Age {health.ageYears.toLocaleString()} · {health.species.toLocaleString()} species ·{" "}
            {(health.snapshots ?? 0).toLocaleString()} snapshots
          </small>
        </article>

        <article className={`ops-card ${ops.destructiveOpsAllowed ? "tone-warn" : "tone-ok"}`}>
          <span className="ops-card-label">Destructive ops</span>
          <strong>
            {ops.destructiveOpsAllowed ? (
              <>
                <Unlock size={15} aria-hidden="true" /> Enabled
              </>
            ) : (
              <>
                <Lock size={15} aria-hidden="true" /> Locked
              </>
            )}
          </strong>
          <small>
            {ops.destructiveOpsAllowed
              ? "Seed reset is permitted (EVOVERSE_ALLOW_DESTRUCTIVE_OPS=true)"
              : "Seed reset returns 403 in this environment"}
          </small>
        </article>

        <article className={`ops-card ${health.persistence === "postgres" ? "tone-ok" : "tone-warn"}`}>
          <span className="ops-card-label">Persistence</span>
          <strong>
            {health.persistence === "postgres" ? (
              <>
                <CircleCheck size={15} aria-hidden="true" /> Postgres
              </>
            ) : (
              <>
                <AlertTriangle size={15} aria-hidden="true" /> {formatToken(health.persistence)}
              </>
            )}
          </strong>
          <small>
            {health.persistence === "postgres"
              ? "API and worker share durable state"
              : "In-memory: API and worker do not share state"}
          </small>
        </article>
      </div>

      {worker ? (
        <p className="ops-worker-line">
          <strong>{worker.workerId}</strong> · {formatToken(worker.status)} · step{" "}
          {worker.lastStep.toLocaleString()} · updated {worker.updatedAt}
          {worker.lastError ? ` · error: ${worker.lastError}` : ""}
        </p>
      ) : (
        <p className="ops-worker-line muted">
          No worker heartbeat yet. Start it with <code>make worker</code> (requires postgres
          persistence).
        </p>
      )}
    </section>
  );
}

function formatToken(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}
