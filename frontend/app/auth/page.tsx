import type { Metadata } from "next";
import type { ReactNode } from "react";
import Link from "next/link";
import { KeyRound, LogIn, LogOut, ServerCog, ShieldCheck, UserRound } from "lucide-react";
import { getIdentityContext } from "@/lib/api";
import { getAuthRuntimeConfig, getServerAuthSession } from "@/lib/authSession";

export const metadata: Metadata = {
  title: "Auth | Evoverse",
  description: "Evoverse Alpha authentication and role gate status."
};

type AuthPageProps = {
  searchParams?: Promise<{
    status?: string | string[];
  }>;
};

export default async function AuthPage({ searchParams }: AuthPageProps) {
  const params = await searchParams;
  const status = Array.isArray(params?.status) ? params.status[0] : params?.status;
  const [identity, session] = await Promise.all([
    getIdentityContext(),
    getServerAuthSession()
  ]);
  const runtime = getAuthRuntimeConfig();
  const providerLabel = runtime.provider === "google" ? "Google Auth" : "Local Alpha";

  return (
    <main className="page-shell auth-page">
      <section className="auth-hero">
        <div>
          <p className="eyebrow">Auth</p>
          <h1>Access Console</h1>
          <p>
            Session, role gate, and trusted backend bridge state for Evoverse Alpha.
          </p>
          {status ? <span className="auth-status-note">{formatToken(status)}</span> : null}
        </div>
        <div className="auth-actions">
          {runtime.googleReady ? (
            <Link className="primary-action" href="/api/auth/google">
              <LogIn size={17} aria-hidden="true" />
              <span>Continue with Google</span>
            </Link>
          ) : (
            <span className="secondary-action auth-action-disabled" aria-disabled="true">
              <LogIn size={17} aria-hidden="true" />
              <span>Google Pending</span>
            </span>
          )}
          {session ? (
            <Link className="secondary-action" href="/api/auth/logout">
              <LogOut size={17} aria-hidden="true" />
              <span>Sign out</span>
            </Link>
          ) : null}
        </div>
      </section>

      <section className="auth-status-grid" aria-label="Authentication status">
        <AuthStatusCard
          icon={<KeyRound size={20} aria-hidden="true" />}
          label="Provider"
          value={providerLabel}
          detail={runtime.googleReady ? "Google runtime ready" : "Local bridge active"}
        />
        <AuthStatusCard
          icon={<UserRound size={20} aria-hidden="true" />}
          label="Session"
          value={session?.userId ?? identity?.users.observer.id ?? "No session"}
          detail={session ? "Cookie session active" : "Fallback identity"}
        />
        <AuthStatusCard
          icon={<ServerCog size={20} aria-hidden="true" />}
          label="BFF Bridge"
          value={runtime.trustedHeaderConfigured ? "Trusted header" : "Open local header"}
          detail={
            identity?.auth.trustedHeaderRequired
              ? "Backend secret required"
              : "Backend secret not required"
          }
        />
        <AuthStatusCard
          icon={<ShieldCheck size={20} aria-hidden="true" />}
          label="Role Gate"
          value={identity?.roleGate.catalystAccess ?? "Unavailable"}
          detail={identity?.roleGate.subscription ?? "Deferred"}
        />
      </section>

      {identity ? (
        <section className="auth-role-panel" aria-label="Current role mapping">
          <header>
            <div>
              <p className="eyebrow">Role Mapping</p>
              <h2>Current Identity Context</h2>
            </div>
            <span>{formatToken(identity.auth.sessionStrategy)}</span>
          </header>
          <div className="auth-role-grid">
            <RoleTile
              label="Observer"
              user={identity.users.observer.id}
              status={identity.capabilities.observer.canFollow ? "Follow enabled" : "Follow gated"}
            />
            <RoleTile
              label="Catalyst"
              user={identity.users.catalyst.id}
              status={`${formatToken(identity.users.catalyst.role)} / ${formatToken(identity.users.catalyst.status)}`}
            />
            <RoleTile
              label="Admin"
              user={identity.users.admin.id}
              status={
                identity.capabilities.admin.canUseAdmin
                  ? "Admin enabled"
                  : formatToken(identity.capabilities.admin.reason ?? "role required")
              }
            />
          </div>
        </section>
      ) : null}
    </main>
  );
}

function AuthStatusCard({
  icon,
  label,
  value,
  detail
}: {
  icon: ReactNode;
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <article className="auth-status-card">
      {icon}
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  );
}

function RoleTile({
  label,
  user,
  status
}: {
  label: string;
  user: string;
  status: string;
}) {
  return (
    <article className="auth-role-tile">
      <span>{label}</span>
      <strong>{user}</strong>
      <small>{status}</small>
    </article>
  );
}

function formatToken(value: string) {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}
