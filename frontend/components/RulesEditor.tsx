"use client";

import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  History,
  Loader2,
  RotateCcw,
  ShieldAlert,
  SlidersHorizontal,
  Undo2,
  XCircle
} from "lucide-react";
import type {
  RuleApplyResponse,
  RuleAuditEntry,
  RuleReloadStrategy,
  RuleRevision,
  RuleRollbackResponse,
  RuleValidationResponse,
  RulesSection
} from "@/lib/types";

type RulesMap = Record<string, RulesSection>;

type RulesEditorProps = {
  initialRules: RulesMap;
  initialRevision: number;
  initialRulesHash: string;
  initialAudit: RuleAuditEntry[];
  initialRevisions: RuleRevision[];
  reloadStrategy: RuleReloadStrategy | null;
  canApply: boolean;
  gateReason: string | null;
};

type RuleField = {
  path: string;
  section: string;
  key: string;
  nestedKey?: string;
  baseline: number;
  isInt: boolean;
};

type RuleChange = RuleField & {
  to: number;
  risk: string | null;
};

const SECTION_ORDER = [
  "catalyst",
  "region",
  "population",
  "speciation",
  "chronicle",
  "speciesStatus",
  "universe"
];

const SECTION_TITLES: Record<string, string> = {
  catalyst: "Catalyst",
  region: "Region",
  population: "Population",
  speciation: "Speciation",
  chronicle: "Chronicle",
  speciesStatus: "Species Status",
  universe: "Universe"
};

export function RulesEditor({
  initialRules,
  initialRevision,
  initialRulesHash,
  initialAudit,
  initialRevisions,
  reloadStrategy,
  canApply,
  gateReason
}: RulesEditorProps) {
  const [baseline, setBaseline] = useState<RulesMap>(initialRules);
  const [revision, setRevision] = useState(initialRevision);
  const [rulesHash, setRulesHash] = useState(initialRulesHash);
  const [audit, setAudit] = useState(initialAudit);
  const [revisions, setRevisions] = useState(initialRevisions);
  const [strategy, setStrategy] = useState<RuleReloadStrategy | null>(reloadStrategy);

  const fields = useMemo(() => buildFields(baseline), [baseline]);
  const [draft, setDraft] = useState<Record<string, string>>(() => initialDraft(fields));

  const [reason, setReason] = useState("");
  const [validation, setValidation] = useState<RuleValidationResponse | null>(null);
  const [confirmRisky, setConfirmRisky] = useState(false);
  const [pending, setPending] = useState<null | "validate" | "apply" | "rollback">(null);
  const [message, setMessage] = useState<{ tone: "ok" | "error"; text: string } | null>(null);

  // Reset the working draft whenever the applied baseline changes.
  useEffect(() => {
    setDraft(initialDraft(fields));
    setValidation(null);
    setConfirmRisky(false);
  }, [fields]);

  const { changes, invalidPaths } = useMemo(
    () => diffDraft(fields, draft),
    [fields, draft]
  );
  const riskyChanges = changes.filter((change) => change.risk !== null);
  const dirty = changes.length > 0;
  const hasInvalid = invalidPaths.length > 0;

  function updateField(path: string, value: string) {
    setDraft((current) => ({ ...current, [path]: value }));
    setMessage(null);
  }

  function resetDraft() {
    setDraft(initialDraft(fields));
    setValidation(null);
    setConfirmRisky(false);
    setMessage(null);
  }

  function buildUpdatePayload(): RulesMap {
    const update: RulesMap = {};
    for (const change of changes) {
      const section = (update[change.section] ??= {}) as Record<string, unknown>;
      if (change.nestedKey) {
        const nested = (section[change.key] ??= {}) as Record<string, number>;
        nested[change.nestedKey] = change.to;
      } else {
        section[change.key] = change.to;
      }
    }
    return update;
  }

  async function refreshHistory() {
    try {
      const response = await fetch("/api/admin/rules/history", { cache: "no-store" });
      if (!response.ok) {
        return;
      }
      const payload = (await response.json()) as {
        audit: RuleAuditEntry[];
        revisions: RuleRevision[];
      };
      setAudit(payload.audit);
      setRevisions(payload.revisions);
    } catch {
      /* history refresh is best-effort */
    }
  }

  async function runValidate() {
    if (!dirty || hasInvalid) {
      return;
    }
    setPending("validate");
    setMessage(null);
    try {
      const response = await fetch("/api/admin/rules/validate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rules: buildUpdatePayload(), reason: reason || undefined })
      });
      const payload = (await response.json()) as RuleValidationResponse;
      setValidation(payload);
      void refreshHistory();
      if (!response.ok) {
        setMessage({ tone: "error", text: "Validation rejected by backend." });
      } else if (payload.valid) {
        setMessage({ tone: "ok", text: "Draft is valid and ready to apply." });
      } else {
        setMessage({ tone: "error", text: "Draft has validation errors." });
      }
    } catch {
      setMessage({ tone: "error", text: "Validation request failed." });
    } finally {
      setPending(null);
    }
  }

  async function runApply() {
    if (!dirty || hasInvalid) {
      return;
    }
    if (riskyChanges.length > 0 && !confirmRisky) {
      setMessage({ tone: "error", text: "Confirm the risky changes before applying." });
      return;
    }
    setPending("apply");
    setMessage(null);
    try {
      const response = await fetch("/api/admin/rules/apply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rules: buildUpdatePayload(), reason: reason || undefined })
      });
      const payload = await response.json();
      if (!response.ok) {
        const detail = payload as RuleValidationResponse | { detail?: string };
        if ("errors" in detail && detail.errors) {
          setValidation(detail as RuleValidationResponse);
        }
        setMessage({
          tone: "error",
          text: `${backendError(payload, "Apply rejected.")} Run Validate to see field-level details.`
        });
        return;
      }
      const applied = payload as RuleApplyResponse;
      setBaseline(applied.rules);
      setRevision(applied.revision);
      setRulesHash(applied.rulesHash);
      setStrategy(applied.reloadStrategy);
      setReason("");
      setMessage({
        tone: "ok",
        text: `Applied revision ${applied.revision}. Worker reloads before its next step.`
      });
      await refreshHistory();
    } catch {
      setMessage({ tone: "error", text: "Apply request failed." });
    } finally {
      setPending(null);
    }
  }

  async function runRollback(targetRevision?: number) {
    setPending("rollback");
    setMessage(null);
    try {
      const response = await fetch("/api/admin/rules/rollback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          targetRevision,
          reason: reason || undefined
        })
      });
      const payload = await response.json();
      if (!response.ok) {
        setMessage({ tone: "error", text: backendError(payload, "Rollback rejected.") });
        return;
      }
      const rolledBack = payload as RuleRollbackResponse;
      setBaseline(rolledBack.rules);
      setRevision(rolledBack.revision);
      setRulesHash(rolledBack.rulesHash);
      setStrategy(rolledBack.reloadStrategy);
      setReason("");
      setMessage({
        tone: "ok",
        text: `Rolled back to revision ${rolledBack.restoredFromRevision} (new revision ${rolledBack.revision}).`
      });
      await refreshHistory();
    } catch {
      setMessage({ tone: "error", text: "Rollback request failed." });
    } finally {
      setPending(null);
    }
  }

  const orderedSections = orderSections(baseline);

  return (
    <div className="rules-editor">
      <section className="rules-editor-status" aria-label="Active rules state">
        <div className="rules-editor-stat">
          <span>Active Revision</span>
          <strong>{revision}</strong>
        </div>
        <div className="rules-editor-stat">
          <span>Rules Hash</span>
          <strong title={rulesHash}>{rulesHash.slice(0, 12)}…</strong>
        </div>
        <div className="rules-editor-stat">
          <span>Pending Changes</span>
          <strong>{changes.length}</strong>
        </div>
        <div className="rules-editor-stat">
          <span>Risky Changes</span>
          <strong className={riskyChanges.length ? "danger" : undefined}>
            {riskyChanges.length}
          </strong>
        </div>
      </section>

      {!canApply ? (
        <p className="rules-editor-gate">
          <ShieldAlert size={16} aria-hidden="true" />
          Editing is gated for this identity{gateReason ? ` (${formatToken(gateReason)})` : ""}. Sign
          in with an admin role to draft, apply, or roll back rules.
        </p>
      ) : null}

      <section className="rules-editor-grid">
        {orderedSections.map(([sectionKey, section]) => (
          <article className="rule-section editable" key={sectionKey}>
            <header>
              <div className="rule-icon">
                <SlidersHorizontal size={18} aria-hidden="true" />
              </div>
              <h2>{SECTION_TITLES[sectionKey] ?? titleize(sectionKey)}</h2>
            </header>
            <div className="rule-list">
              {Object.entries(section).map(([key, value]) =>
                isNested(value) ? (
                  <div className="rule-row nested-rule" key={key}>
                    <span>{titleize(key)}</span>
                    <div>
                      {Object.keys(value).map((nestedKey) => {
                        const path = `${sectionKey}.${key}.${nestedKey}`;
                        return (
                          <RuleInput
                            key={path}
                            label={formatToken(nestedKey)}
                            path={path}
                            draft={draft}
                            fields={fields}
                            disabled={!canApply || pending !== null}
                            onChange={updateField}
                          />
                        );
                      })}
                    </div>
                  </div>
                ) : (
                  <div className="rule-row editable-row" key={key}>
                    <span>{titleize(key)}</span>
                    <RuleInput
                      label=""
                      path={`${sectionKey}.${key}`}
                      draft={draft}
                      fields={fields}
                      disabled={!canApply || pending !== null}
                      onChange={updateField}
                    />
                  </div>
                )
              )}
            </div>
          </article>
        ))}
      </section>

      {dirty ? (
        <section className="rules-diff" aria-label="Pending change preview">
          <header>
            <h3>Change Preview</h3>
            <span>{changes.length} field(s)</span>
          </header>
          <ul>
            {changes.map((change) => (
              <li key={change.path} className={change.risk ? "risky" : undefined}>
                <code>{change.path}</code>
                <span className="diff-values">
                  {formatNumber(change.baseline)} <span aria-hidden="true">→</span>{" "}
                  <strong>{formatNumber(change.to)}</strong>
                </span>
                {change.risk ? (
                  <span className="diff-risk">
                    <AlertTriangle size={13} aria-hidden="true" />
                    {change.risk}
                  </span>
                ) : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {validation ? <ValidationPanel validation={validation} /> : null}

      {strategy ? (
        <section className="rules-reload" aria-label="Reload strategy">
          <h3>Hot Reload Strategy</h3>
          <div>
            <span>
              API <strong>{formatToken(strategy.api.mode)}</strong> /{" "}
              {formatToken(strategy.api.status)}
            </span>
            <span>
              Worker <strong>{formatToken(strategy.worker.mode)}</strong> /{" "}
              {formatToken(strategy.worker.status)}
            </span>
            <span>Restart required: {strategy.restartRequired ? "yes" : "no"}</span>
          </div>
        </section>
      ) : null}

      <section className="rules-actions" aria-label="Rule change actions">
        <label className="rules-reason">
          <span>Reason (audit log)</span>
          <input
            type="text"
            value={reason}
            placeholder="e.g. Calm speciation cadence"
            disabled={!canApply || pending !== null}
            onChange={(event) => setReason(event.target.value)}
          />
        </label>

        {hasInvalid ? (
          <p className="rules-inline-warn">
            <XCircle size={14} aria-hidden="true" />
            {invalidPaths.length} field(s) are not valid numbers.
          </p>
        ) : null}

        {riskyChanges.length > 0 && canApply ? (
          <label className="rules-confirm-risky">
            <input
              type="checkbox"
              checked={confirmRisky}
              disabled={pending !== null}
              onChange={(event) => setConfirmRisky(event.target.checked)}
            />
            <span>
              I understand {riskyChanges.length} risky change(s) may destabilize Alpha.
            </span>
          </label>
        ) : null}

        <div className="rules-action-buttons">
          <button
            type="button"
            className="ghost"
            disabled={!dirty || pending !== null}
            onClick={resetDraft}
          >
            <Undo2 size={15} aria-hidden="true" />
            Reset draft
          </button>
          <button
            type="button"
            disabled={!canApply || !dirty || hasInvalid || pending !== null}
            onClick={runValidate}
          >
            {pending === "validate" ? (
              <Loader2 size={15} aria-hidden="true" className="spin" />
            ) : (
              <CheckCircle2 size={15} aria-hidden="true" />
            )}
            Validate
          </button>
          <button
            type="button"
            className="primary"
            disabled={
              !canApply ||
              !dirty ||
              hasInvalid ||
              pending !== null ||
              (riskyChanges.length > 0 && !confirmRisky)
            }
            onClick={runApply}
          >
            {pending === "apply" ? (
              <Loader2 size={15} aria-hidden="true" className="spin" />
            ) : (
              <SlidersHorizontal size={15} aria-hidden="true" />
            )}
            Apply changes
          </button>
          <button
            type="button"
            className="ghost"
            disabled={!canApply || pending !== null || revisions.length < 2}
            onClick={() => void runRollback()}
            title="Roll back to the previous applied revision"
          >
            <RotateCcw size={15} aria-hidden="true" />
            Rollback latest
          </button>
        </div>

        {message ? (
          <p className={message.tone === "ok" ? "rules-message ok" : "rules-message error"}>
            {message.tone === "ok" ? (
              <CheckCircle2 size={15} aria-hidden="true" />
            ) : (
              <XCircle size={15} aria-hidden="true" />
            )}
            {message.text}
          </p>
        ) : null}
      </section>

      <div className="rules-history-grid">
        <section className="rules-revisions" aria-label="Revision history">
          <header>
            <History size={16} aria-hidden="true" />
            <h3>Revisions</h3>
          </header>
          {revisions.length ? (
            <ul>
              {revisions.map((item) => (
                <li key={item.id} className={item.isActive ? "active" : undefined}>
                  <div>
                    <strong>r{item.revision}</strong>
                    {item.isActive ? <span className="badge">active</span> : null}
                    <code>{item.rulesHash.slice(0, 10)}</code>
                  </div>
                  <small>
                    {item.appliedBy}
                    {item.reason ? ` · ${item.reason}` : ""}
                  </small>
                  {canApply && !item.isActive ? (
                    <button
                      type="button"
                      className="ghost small"
                      disabled={pending !== null}
                      onClick={() => void runRollback(item.revision)}
                    >
                      <RotateCcw size={13} aria-hidden="true" />
                      Restore
                    </button>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : (
            <p className="rules-empty">No persisted revisions yet.</p>
          )}
        </section>

        <section className="rules-audit" aria-label="Audit log">
          <header>
            <History size={16} aria-hidden="true" />
            <h3>Audit Log</h3>
          </header>
          {audit.length ? (
            <ul>
              {audit.map((entry) => (
                <li key={entry.id} className={entry.status === "rejected" ? "rejected" : undefined}>
                  <div>
                    <strong>{formatToken(entry.actionType)}</strong>
                    <span className={`audit-status ${entry.status}`}>{entry.status}</span>
                    {entry.targetRevision !== null ? (
                      <code>r{entry.targetRevision}</code>
                    ) : null}
                  </div>
                  <small>
                    {entry.actorId}
                    {entry.reason ? ` · ${entry.reason}` : ""}
                  </small>
                </li>
              ))}
            </ul>
          ) : (
            <p className="rules-empty">No audit entries yet.</p>
          )}
        </section>
      </div>
    </div>
  );
}

function RuleInput({
  label,
  path,
  draft,
  fields,
  disabled,
  onChange
}: {
  label: string;
  path: string;
  draft: Record<string, string>;
  fields: RuleField[];
  disabled: boolean;
  onChange: (path: string, value: string) => void;
}) {
  const field = fields.find((item) => item.path === path);
  const raw = draft[path] ?? "";
  const changed = field ? Number(raw) !== field.baseline && raw.trim() !== "" : false;
  const invalid = raw.trim() === "" || Number.isNaN(Number(raw));
  return (
    <label className={`rule-input${changed ? " changed" : ""}${invalid ? " invalid" : ""}`}>
      {label ? <span>{label}</span> : null}
      <input
        type="number"
        inputMode="decimal"
        step={field?.isInt ? 1 : "any"}
        value={raw}
        disabled={disabled}
        onChange={(event) => onChange(path, event.target.value)}
      />
    </label>
  );
}

function ValidationPanel({ validation }: { validation: RuleValidationResponse }) {
  return (
    <section
      className={`rules-validation ${validation.valid ? "valid" : "invalid"}`}
      aria-label="Validation result"
    >
      <header>
        {validation.valid ? (
          <CheckCircle2 size={16} aria-hidden="true" />
        ) : (
          <XCircle size={16} aria-hidden="true" />
        )}
        <h3>{validation.valid ? "Draft validated" : "Validation failed"}</h3>
        <code>{validation.rulesHash.slice(0, 12)}</code>
      </header>
      {validation.errors.length ? (
        <div className="rules-issue-list errors">
          <h4>Errors</h4>
          <ul>
            {validation.errors.map((issue) => (
              <li key={`${issue.path}-${issue.message}`}>
                <code>{issue.path}</code>
                {issue.message}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {validation.warnings.length ? (
        <div className="rules-issue-list warnings">
          <h4>Warnings</h4>
          <ul>
            {validation.warnings.map((issue) => (
              <li key={`${issue.path}-${issue.message}`}>
                <AlertTriangle size={13} aria-hidden="true" />
                <code>{issue.path}</code>
                {issue.message}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {validation.valid && !validation.warnings.length ? (
        <p>No warnings. Safe to apply.</p>
      ) : null}
    </section>
  );
}

function buildFields(rules: RulesMap): RuleField[] {
  const fields: RuleField[] = [];
  for (const [section, sectionValue] of Object.entries(rules)) {
    for (const [key, value] of Object.entries(sectionValue)) {
      if (isNested(value)) {
        for (const [nestedKey, nestedValue] of Object.entries(value)) {
          if (typeof nestedValue === "number") {
            fields.push({
              path: `${section}.${key}.${nestedKey}`,
              section,
              key,
              nestedKey,
              baseline: nestedValue,
              isInt: Number.isInteger(nestedValue)
            });
          }
        }
      } else if (typeof value === "number") {
        fields.push({
          path: `${section}.${key}`,
          section,
          key,
          baseline: value,
          isInt: Number.isInteger(value)
        });
      }
    }
  }
  return fields;
}

function initialDraft(fields: RuleField[]): Record<string, string> {
  const draft: Record<string, string> = {};
  for (const field of fields) {
    draft[field.path] = String(field.baseline);
  }
  return draft;
}

function diffDraft(
  fields: RuleField[],
  draft: Record<string, string>
): { changes: RuleChange[]; invalidPaths: string[] } {
  const changes: RuleChange[] = [];
  const invalidPaths: string[] = [];
  for (const field of fields) {
    const raw = draft[field.path];
    if (raw === undefined || raw.trim() === "") {
      invalidPaths.push(field.path);
      continue;
    }
    const value = Number(raw);
    if (Number.isNaN(value)) {
      invalidPaths.push(field.path);
      continue;
    }
    if (value !== field.baseline) {
      changes.push({ ...field, to: value, risk: riskFor(field, value) });
    }
  }
  return { changes, invalidPaths };
}

function riskFor(field: RuleField, to: number): string | null {
  const path = `${field.section}.${field.key}`.toLowerCase();
  if (/(collapse|recovery|forced|extinct)/.test(path)) {
    return "Collapse / recovery threshold";
  }
  if (field.section === "catalyst" && field.nestedKey) {
    return "Catalyst quota change";
  }
  const base = Math.abs(field.baseline);
  if (base > 0 && Math.abs(to - field.baseline) / base > 0.5) {
    return "Large (>50%) change";
  }
  if (field.baseline === 0 && to !== 0) {
    return "Enables a zero-valued rule";
  }
  return null;
}

function orderSections(rules: RulesMap): Array<[string, RulesSection]> {
  const known = SECTION_ORDER.filter((key) => key in rules).map(
    (key) => [key, rules[key]] as [string, RulesSection]
  );
  const remaining = Object.entries(rules).filter(([key]) => !SECTION_ORDER.includes(key));
  return [...known, ...remaining];
}

function backendError(payload: unknown, fallback: string): string {
  if (payload && typeof payload === "object") {
    const detail = (payload as { detail?: unknown }).detail;
    if (typeof detail === "string") {
      return detail;
    }
    if (detail && typeof detail === "object") {
      const message = (detail as { message?: unknown }).message;
      if (typeof message === "string") {
        return message;
      }
    }
    // Standard API error envelope: { error: { code, message, status } }.
    const error = (payload as { error?: unknown }).error;
    if (error && typeof error === "object") {
      const message = (error as { message?: unknown }).message;
      if (typeof message === "string") {
        return message;
      }
    }
  }
  return fallback;
}

function isNested(value: unknown): value is Record<string, number> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function titleize(value: string) {
  return value.replace(/([A-Z])/g, " $1").replace(/^./, (letter) => letter.toUpperCase());
}

function formatToken(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatNumber(value: number) {
  return Number.isInteger(value) ? value.toString() : value.toFixed(3);
}
