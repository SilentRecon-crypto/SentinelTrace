import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { FileWarning, UserRoundSearch, MapPinned, PinOff, FolderSearch, Link2, FileText, Gavel, ScrollText } from "lucide-react";
import { useWorkspace } from "@/hooks/useWorkspace";
import { useAsync } from "@/hooks/useAsync";
import { PageHeader } from "@/components/ui/PageHeader";
import { RiskBadge } from "@/components/ui/RiskBadge";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState, ErrorState } from "@/components/ui/States";
import { SkeletonBlock } from "@/components/ui/Skeleton";
import { timeAgo, formatDateTime } from "@/utils/format";
import type { InvestigationPin } from "@/types";
import { analystPath } from "@/routes";
import {
  openCaseForAlert,
  getCase,
  updateCase,
  getCaseNotes,
  addCaseNote,
  getCaseEvidence,
  addCaseEvidence,
  getCaseResolution,
  submitCaseResolution,
  getCaseDossier,
  extractCaseIdFromDuplicateMessage,
  type CaseEvidenceCreatePayload,
} from "@/services/cases";
import { ApiError } from "@/services/httpClient";
import type { BackendCase } from "@/services/backendTypes";

// ============================================================
// INTEGRATION STATUS (Slice 4): adds the real backend Case + Notes +
// Evidence + Resolution + Dossier workflow (Stages 6-9) as a NEW,
// ADDITIVE "Backend Case" section on this page. The existing pinboard
// above (session-local, unchanged) is preserved exactly as-is — they are
// two different things (working scratch space vs. persisted investigation
// record) and are not merged.
//
// No standalone Alerts page/service exists yet in this frontend (that is
// a separate future integration slice), so the only way to open a case is
// via its alert_id — the backend's own POST /alerts/{alert_id}/cases path
// param. Until Alerts are integrated, the analyst enters an alert_id
// manually (e.g. copied from Swagger or a prior integration step), or
// opens an already-known case_id directly. This is disclosed in the UI
// text below, not hidden.
//
// The 4 case statuses, 3 evidence types, and 4 resolution outcome types
// below are the backend's exact, closed sets (app/core/case_config.py,
// evidence_config.py, resolution_config.py) — nothing invented, nothing
// extra offered.
// ============================================================

const CASE_STATUSES = ["open", "investigating", "escalated", "resolved"] as const;
const EVIDENCE_TYPES = [
  { value: "transaction_reference", label: "Transaction Reference" },
  { value: "graph_explanation_reference", label: "Graph / Explanation Reference" },
  { value: "risk_driver_reference", label: "Risk Driver Reference" },
] as const;
const RESOLUTION_OUTCOMES = ["confirmed_mule", "false_positive", "insufficient_evidence", "referred_external"] as const;

const inputCls =
  "w-full rounded-sm border border-[color:var(--color-border-strong)] bg-[color:var(--color-surface)] px-2.5 py-1.5 text-[12.5px] text-[color:var(--color-text-primary)] placeholder:text-[color:var(--color-text-tertiary)] focus:border-[color:var(--color-signal)] focus:outline-none";
const btnPrimaryCls =
  "rounded-sm bg-[color:var(--color-signal)] px-3 py-1.5 text-[12px] font-semibold text-[#04191c] hover:opacity-90 disabled:opacity-50";
const btnSecondaryCls =
  "rounded-sm border border-[color:var(--color-border-strong)] px-3 py-1.5 text-[12px] font-medium text-[color:var(--color-text-secondary)] hover:border-[color:var(--color-signal)] hover:text-[color:var(--color-signal)] disabled:opacity-50";
const panelCls = "rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)]";

function CaseEntryPanel({ onCaseOpened }: { onCaseOpened: (caseId: string) => void }) {
  const [alertId, setAlertId] = useState("");
  const [caseIdInput, setCaseIdInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ text: string; existingCaseId?: string } | null>(null);

  async function handleOpenFromAlert() {
    if (!alertId.trim()) return;
    setBusy(true);
    setMessage(null);
    try {
      const created = await openCaseForAlert(alertId.trim());
      onCaseOpened(created.case_id);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        const existingId = extractCaseIdFromDuplicateMessage(err.message);
        setMessage({ text: err.message, existingCaseId: existingId ?? undefined });
      } else {
        setMessage({ text: err instanceof Error ? err.message : "Could not open a case for this alert." });
      }
    } finally {
      setBusy(false);
    }
  }

  function handleOpenById() {
    if (caseIdInput.trim()) onCaseOpened(caseIdInput.trim());
  }

  return (
    <div className={panelCls}>
      <div className="flex items-center gap-2 border-b border-[color:var(--color-border)] px-4 py-3">
        <Link2 className="h-3.5 w-3.5 text-[color:var(--color-signal)]" strokeWidth={1.75} />
        <h2 className="text-[12.5px] font-semibold text-[color:var(--color-text-primary)]">Open a Backend Case</h2>
      </div>
      <div className="space-y-3 px-4 py-4">
        <p className="text-[11.5px] leading-snug text-[color:var(--color-text-tertiary)]">
          Alerts now generate a "Create Case" action directly on the Complaint Detail page — this panel remains for manually opening a case by ID (recovery, or picking up a case from a previous session).
        </p>
        <div className="flex items-end gap-2">
          <div className="flex-1">
            <label className="mb-1 block text-[10.5px] uppercase tracking-wide text-[color:var(--color-text-tertiary)]">Alert ID</label>
            <input className={inputCls} value={alertId} onChange={(e) => setAlertId(e.target.value)} placeholder="alert UUID" />
          </div>
          <button onClick={handleOpenFromAlert} disabled={busy || !alertId.trim()} className={btnPrimaryCls}>
            {busy ? "Opening…" : "Create / Open Case"}
          </button>
        </div>
        <div className="flex items-end gap-2">
          <div className="flex-1">
            <label className="mb-1 block text-[10.5px] uppercase tracking-wide text-[color:var(--color-text-tertiary)]">Case ID</label>
            <input className={inputCls} value={caseIdInput} onChange={(e) => setCaseIdInput(e.target.value)} placeholder="existing case UUID" />
          </div>
          <button onClick={handleOpenById} disabled={!caseIdInput.trim()} className={btnSecondaryCls}>
            Open Case
          </button>
        </div>
        {message && (
          <div className="rounded-sm border border-[color:var(--color-border-strong)] px-3 py-2 text-[11.5px] text-[color:var(--color-text-secondary)]">
            {message.text}
            {message.existingCaseId && (
              <button onClick={() => onCaseOpened(message.existingCaseId!)} className="ml-2 font-medium text-[color:var(--color-signal)] hover:underline">
                Open it
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function CaseStatusPanel({ caseData, onUpdated }: { caseData: BackendCase; onUpdated: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [assignedToInput, setAssignedToInput] = useState(caseData.assigned_to ?? "");

  async function handleStatusChange(status: string) {
    if (status === caseData.status) return;
    setBusy(true);
    setError(null);
    try {
      await updateCase(caseData.case_id, { status });
      onUpdated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Status update failed.");
    } finally {
      setBusy(false);
    }
  }

  async function handleSaveAssignment() {
    setBusy(true);
    setError(null);
    try {
      await updateCase(caseData.case_id, { assignedTo: assignedToInput.trim() === "" ? null : assignedToInput.trim() });
      onUpdated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Assignment update failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={panelCls}>
      <div className="border-b border-[color:var(--color-border)] px-4 py-3">
        <h2 className="text-[12.5px] font-semibold text-[color:var(--color-text-primary)]">
          Case <span className="mono-id text-[color:var(--color-text-tertiary)]">{caseData.case_id}</span>
        </h2>
      </div>
      <div className="space-y-3 px-4 py-4">
        <div className="flex flex-wrap items-center gap-4 text-[11.5px] text-[color:var(--color-text-tertiary)]">
          <span>Complaint <span className="mono-id text-[color:var(--color-text-secondary)]">{caseData.complaint_id}</span></span>
          <span>Account <span className="mono-id text-[color:var(--color-text-secondary)]">ACC-{caseData.account_id}</span></span>
          <StatusBadge status={caseData.status} />
        </div>
        <div>
          <label className="mb-1 block text-[10.5px] uppercase tracking-wide text-[color:var(--color-text-tertiary)]">Status</label>
          <div className="flex flex-wrap gap-1.5">
            {CASE_STATUSES.map((s) => (
              <button
                key={s}
                onClick={() => handleStatusChange(s)}
                disabled={busy || s === caseData.status}
                className={s === caseData.status ? btnPrimaryCls : btnSecondaryCls}
              >
                {s}
              </button>
            ))}
          </div>
        </div>
        <div className="flex items-end gap-2">
          <div className="flex-1">
            <label className="mb-1 block text-[10.5px] uppercase tracking-wide text-[color:var(--color-text-tertiary)]">Assigned To (free text — no auth system exists)</label>
            <input className={inputCls} value={assignedToInput} onChange={(e) => setAssignedToInput(e.target.value)} placeholder="investigator name/id" />
          </div>
          <button onClick={handleSaveAssignment} disabled={busy} className={btnSecondaryCls}>
            Save
          </button>
        </div>
        {error && <p className="text-[11px] text-[color:var(--color-critical)]">{error}</p>}
      </div>
    </div>
  );
}

function CaseNotesPanel({ caseId }: { caseId: string }) {
  const { data: notes, loading, error, reload } = useAsync(() => getCaseNotes(caseId), [caseId]);
  const [author, setAuthor] = useState("");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);

  async function handleAdd() {
    if (!author.trim() || !text.trim()) return;
    setBusy(true);
    setAddError(null);
    try {
      await addCaseNote(caseId, author.trim(), text.trim());
      setText("");
      reload();
    } catch (err) {
      // Previously unhandled — a failed POST (e.g. the case was deleted by
      // a risk recalculation elsewhere) silently cleared the busy state
      // with no indication to the analyst. Fixed to match every other
      // mutation handler on this page (Status/Evidence/Resolution).
      setAddError(err instanceof Error ? err.message : "Could not add note.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={panelCls}>
      <div className="flex items-center gap-2 border-b border-[color:var(--color-border)] px-4 py-3">
        <FileText className="h-3.5 w-3.5 text-[color:var(--color-signal)]" strokeWidth={1.75} />
        <h2 className="text-[12.5px] font-semibold text-[color:var(--color-text-primary)]">Investigator Notes</h2>
      </div>
      <div className="px-4 py-3">
        {error ? (
          <ErrorState message={error} onRetry={reload} />
        ) : loading ? (
          <SkeletonBlock className="h-16" />
        ) : !notes || notes.length === 0 ? (
          <p className="py-2 text-[12px] text-[color:var(--color-text-tertiary)]">No notes yet.</p>
        ) : (
          <div className="mb-3 space-y-2">
            {notes.map((n) => (
              <div key={n.note_id} className="rounded-sm border border-[color:var(--color-border)] px-3 py-2">
                <div className="mb-0.5 flex items-center justify-between text-[10.5px] text-[color:var(--color-text-tertiary)]">
                  <span className="font-medium text-[color:var(--color-text-secondary)]">{n.author}</span>
                  <span>{timeAgo(n.created_at)}</span>
                </div>
                <p className="text-[12px] text-[color:var(--color-text-secondary)]">{n.note_text}</p>
              </div>
            ))}
          </div>
        )}
        <div className="space-y-2">
          <input className={inputCls} value={author} onChange={(e) => setAuthor(e.target.value)} placeholder="Author" />
          <textarea className={inputCls} rows={2} value={text} onChange={(e) => setText(e.target.value)} placeholder="Add a note (append-only)…" />
          <button onClick={handleAdd} disabled={busy || !author.trim() || !text.trim()} className={btnPrimaryCls}>
            {busy ? "Adding…" : "Add Note"}
          </button>
          {addError && <p className="text-[11px] text-[color:var(--color-critical)]">{addError}</p>}
        </div>
      </div>
    </div>
  );
}

function CaseEvidencePanel({ caseId }: { caseId: string }) {
  const { data: evidence, loading, error, reload } = useAsync(() => getCaseEvidence(caseId), [caseId]);
  const [evidenceType, setEvidenceType] = useState<CaseEvidenceCreatePayload["evidence_type"]>("transaction_reference");
  const [transactionId, setTransactionId] = useState("");
  const [predictionId, setPredictionId] = useState("");
  const [riskScoreId, setRiskScoreId] = useState("");
  const [driverIndex, setDriverIndex] = useState("");
  const [note, setNote] = useState("");
  const [addedBy, setAddedBy] = useState("");
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function handleAdd() {
    if (!addedBy.trim()) return;
    setBusy(true);
    setFormError(null);
    try {
      const payload: CaseEvidenceCreatePayload = { evidence_type: evidenceType, added_by: addedBy.trim(), note: note.trim() || undefined };
      if (evidenceType === "transaction_reference") payload.transaction_id = Number(transactionId);
      if (evidenceType === "graph_explanation_reference") payload.prediction_id = Number(predictionId);
      if (evidenceType === "risk_driver_reference") {
        payload.risk_score_id = riskScoreId.trim();
        if (driverIndex.trim() !== "") payload.driver_index = Number(driverIndex);
      }
      await addCaseEvidence(caseId, payload);
      // Previously only `note` was cleared, leaving the type-specific
      // reference fields populated after a successful submit — a repeat
      // click of "Attach Evidence" would silently resubmit the same
      // reference. Fixed to clear all reference fields, matching the
      // Notes panel's established convention of clearing input but
      // keeping the investigator identifier (`addedBy`) populated.
      setTransactionId("");
      setPredictionId("");
      setRiskScoreId("");
      setDriverIndex("");
      setNote("");
      reload();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Could not attach evidence.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={panelCls}>
      <div className="flex items-center gap-2 border-b border-[color:var(--color-border)] px-4 py-3">
        <ScrollText className="h-3.5 w-3.5 text-[color:var(--color-signal)]" strokeWidth={1.75} />
        <h2 className="text-[12.5px] font-semibold text-[color:var(--color-text-primary)]">Structured Evidence</h2>
      </div>
      <div className="px-4 py-3">
        <p className="mb-2 text-[11px] text-[color:var(--color-text-tertiary)]">
          References to existing SentinelTrace intelligence only — not file upload.
        </p>
        {error ? (
          <ErrorState message={error} onRetry={reload} />
        ) : loading ? (
          <SkeletonBlock className="h-16" />
        ) : !evidence || evidence.length === 0 ? (
          <p className="py-2 text-[12px] text-[color:var(--color-text-tertiary)]">No evidence attached yet.</p>
        ) : (
          <div className="mb-3 space-y-1.5">
            {evidence.map((e) => (
              <div key={e.evidence_id} className="flex items-center gap-2 rounded-sm border border-[color:var(--color-border)] px-3 py-2 text-[11.5px]">
                <span className="rounded-[3px] border border-[color:var(--color-border-strong)] px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-[color:var(--color-text-tertiary)]">
                  {e.evidence_type.replace("_reference", "").replace("_", " ")}
                </span>
                <span className="mono-id text-[color:var(--color-text-secondary)]">
                  {e.transaction_id != null && `txn ${e.transaction_id}`}
                  {e.prediction_id != null && `prediction ${e.prediction_id}`}
                  {e.risk_score_id != null && `risk ${e.risk_score_id}${e.driver_index != null ? ` [driver ${e.driver_index}]` : ""}`}
                </span>
                {e.note && <span className="text-[color:var(--color-text-tertiary)]">— {e.note}</span>}
              </div>
            ))}
          </div>
        )}
        <div className="space-y-2">
          <select className={inputCls} value={evidenceType} onChange={(e) => setEvidenceType(e.target.value as CaseEvidenceCreatePayload["evidence_type"])}>
            {EVIDENCE_TYPES.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
          {evidenceType === "transaction_reference" && (
            <input className={inputCls} value={transactionId} onChange={(e) => setTransactionId(e.target.value)} placeholder="Transaction ID" type="number" />
          )}
          {evidenceType === "graph_explanation_reference" && (
            <input className={inputCls} value={predictionId} onChange={(e) => setPredictionId(e.target.value)} placeholder="Prediction ID" type="number" />
          )}
          {evidenceType === "risk_driver_reference" && (
            <>
              <input className={inputCls} value={riskScoreId} onChange={(e) => setRiskScoreId(e.target.value)} placeholder="Risk Score ID (UUID)" />
              <input className={inputCls} value={driverIndex} onChange={(e) => setDriverIndex(e.target.value)} placeholder="Driver Index (optional)" type="number" />
            </>
          )}
          <input className={inputCls} value={note} onChange={(e) => setNote(e.target.value)} placeholder="Note (optional)" />
          <input className={inputCls} value={addedBy} onChange={(e) => setAddedBy(e.target.value)} placeholder="Added By" />
          <button onClick={handleAdd} disabled={busy || !addedBy.trim()} className={btnPrimaryCls}>
            {busy ? "Attaching…" : "Attach Evidence"}
          </button>
          {formError && <p className="text-[11px] text-[color:var(--color-critical)]">{formError}</p>}
        </div>
      </div>
    </div>
  );
}

function CaseResolutionPanel({ caseId }: { caseId: string }) {
  const { data: resolution, loading, error, reload } = useAsync(() => getCaseResolution(caseId), [caseId]);
  const [outcome, setOutcome] = useState<(typeof RESOLUTION_OUTCOMES)[number]>("confirmed_mule");
  const [note, setNote] = useState("");
  const [recordedBy, setRecordedBy] = useState("");
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function handleSubmit() {
    if (!recordedBy.trim()) return;
    setBusy(true);
    setFormError(null);
    try {
      await submitCaseResolution(caseId, { outcome_type: outcome, resolution_note: note.trim() || undefined, recorded_by: recordedBy.trim() });
      reload();
    } catch (err) {
      // Backend enforces "case must be status=resolved" and "one resolution
      // per case" — surfaced here verbatim, never bypassed client-side.
      setFormError(err instanceof Error ? err.message : "Could not submit resolution.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={panelCls}>
      <div className="flex items-center gap-2 border-b border-[color:var(--color-border)] px-4 py-3">
        <Gavel className="h-3.5 w-3.5 text-[color:var(--color-signal)]" strokeWidth={1.75} />
        <h2 className="text-[12.5px] font-semibold text-[color:var(--color-text-primary)]">Resolution</h2>
      </div>
      <div className="px-4 py-3">
        {error ? (
          <ErrorState message={error} onRetry={reload} />
        ) : loading ? (
          <SkeletonBlock className="h-16" />
        ) : resolution ? (
          <div className="rounded-sm border border-[color:var(--color-border)] px-3 py-2.5">
            <div className="mb-1 flex items-center gap-2">
              <span className="rounded-[3px] border border-[color:var(--color-border-strong)] px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-[color:var(--color-text-secondary)]">
                {resolution.outcome_type}
              </span>
              <span className="text-[10.5px] text-[color:var(--color-text-tertiary)]">by {resolution.recorded_by} · {timeAgo(resolution.created_at)}</span>
            </div>
            {resolution.resolution_note && <p className="text-[12px] text-[color:var(--color-text-secondary)]">{resolution.resolution_note}</p>}
          </div>
        ) : (
          <>
            <p className="mb-2 text-[12px] text-[color:var(--color-text-tertiary)]">
              Not yet resolved. Submitting requires the case status to already be "resolved" — an explicit action, not automatic.
            </p>
            <div className="space-y-2">
              <select className={inputCls} value={outcome} onChange={(e) => setOutcome(e.target.value as (typeof RESOLUTION_OUTCOMES)[number])}>
                {RESOLUTION_OUTCOMES.map((o) => (
                  <option key={o} value={o}>{o}</option>
                ))}
              </select>
              <input className={inputCls} value={note} onChange={(e) => setNote(e.target.value)} placeholder="Resolution note (optional)" />
              <input className={inputCls} value={recordedBy} onChange={(e) => setRecordedBy(e.target.value)} placeholder="Recorded By" />
              <button onClick={handleSubmit} disabled={busy || !recordedBy.trim()} className={btnPrimaryCls}>
                {busy ? "Submitting…" : "Submit Resolution"}
              </button>
              {formError && <p className="text-[11px] text-[color:var(--color-critical)]">{formError}</p>}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function CaseDossierPanel({ caseId }: { caseId: string }) {
  const { data: dossier, loading, error, reload } = useAsync(() => getCaseDossier(caseId), [caseId]);

  return (
    <div className={panelCls}>
      <div className="border-b border-[color:var(--color-border)] px-4 py-3">
        <h2 className="text-[12.5px] font-semibold text-[color:var(--color-text-primary)]">Dossier — Pipeline Context</h2>
      </div>
      <div className="px-4 py-3">
        {error ? (
          <ErrorState message={error} onRetry={reload} />
        ) : loading || !dossier ? (
          <SkeletonBlock className="h-24" />
        ) : (
          <div className="space-y-3">
            {dossier.alert && (
              <div className="flex flex-wrap items-center gap-3 text-[11.5px]">
                <span className="text-[color:var(--color-text-tertiary)]">Alert:</span>
                <span className="mono-id text-[color:var(--color-text-secondary)]">{dossier.alert.alert_type}</span>
                <RiskBadge risk={dossier.alert.severity as "critical" | "high" | "medium" | "low"} size="sm" />
              </div>
            )}
            {dossier.risk && (
              <div className="flex flex-wrap items-center gap-3 text-[11.5px]">
                <span className="text-[color:var(--color-text-tertiary)]">Risk:</span>
                <span className="mono-id text-[color:var(--color-text-secondary)]">ML {(dossier.risk.ml_score * 100).toFixed(1)}%</span>
                <span className="mono-id text-[color:var(--color-text-secondary)]">Priority {dossier.risk.priority.value.toFixed(3)}</span>
                <RiskBadge risk={dossier.risk.priority.level as "critical" | "high" | "medium" | "low"} size="sm" />
              </div>
            )}
            {dossier.intervention && (
              <div className="flex flex-wrap items-center gap-3 text-[11.5px]">
                <span className="text-[color:var(--color-text-tertiary)]">Intervention:</span>
                <span className="mono-id text-[color:var(--color-text-secondary)]">{dossier.intervention.estimated_window_minutes} min</span>
                <span className="text-[10.5px] text-[color:var(--color-text-tertiary)]">({dossier.intervention.validation_status})</span>
              </div>
            )}
            {dossier.prediction && (
              <div className="flex flex-wrap items-center gap-3 text-[11.5px]">
                <span className="text-[color:var(--color-text-tertiary)]">Model A:</span>
                <span className="mono-id text-[color:var(--color-text-secondary)]">rank {dossier.prediction.rank}, {(dossier.prediction.model_score * 100).toFixed(1)}%</span>
              </div>
            )}
            {dossier.limitations.length > 0 && (
              <div className="rounded-sm border border-[color:var(--color-border)] px-3 py-2">
                <p className="mb-1 text-[10.5px] uppercase tracking-wide text-[color:var(--color-text-tertiary)]">Limitations (from backend)</p>
                <ul className="space-y-1">
                  {dossier.limitations.map((l, i) => (
                    <li key={i} className="text-[11px] text-[color:var(--color-text-tertiary)]">{l}</li>
                  ))}
                </ul>
              </div>
            )}
            <p className="text-[10.5px] text-[color:var(--color-text-tertiary)]">Case created {formatDateTime(dossier.case.created_at)} · updated {formatDateTime(dossier.case.updated_at)}</p>
          </div>
        )}
      </div>
    </div>
  );
}

function BackendCaseSection() {
  const [params, setParams] = useSearchParams();
  const [activeCaseId, setActiveCaseId] = useState<string | null>(params.get("case"));
  const { data: caseData, loading, error, reload } = useAsync(
    () => (activeCaseId ? getCase(activeCaseId) : Promise.resolve(null)),
    [activeCaseId]
  );

  // Keeps the URL in sync when a case is opened — otherwise a page refresh
  // while a case is active would silently lose it, reverting to the entry
  // panel (the mirror-image of the "Close case" issue above; discovered
  // during the same Slice 6 navigation audit).
  function openCase(caseId: string) {
    setActiveCaseId(caseId);
    const next = new URLSearchParams(params);
    next.set("case", caseId);
    setParams(next, { replace: true });
  }

  // Keeps the URL in sync when a case is closed — otherwise a page refresh
  // after "Close case" would silently reopen it, since the ?case= param
  // would still be present (discovered during the Slice 6 navigation audit).
  function handleClose() {
    setActiveCaseId(null);
    const next = new URLSearchParams(params);
    next.delete("case");
    setParams(next, { replace: true });
  }

  return (
    <div className="mt-4 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-[13px] font-semibold text-[color:var(--color-text-primary)]">Backend Investigation Case</h2>
        {activeCaseId && (
          <button onClick={handleClose} className="text-[11px] font-medium text-[color:var(--color-text-tertiary)] hover:text-[color:var(--color-text-secondary)]">
            Close case
          </button>
        )}
      </div>

      {!activeCaseId ? (
        <CaseEntryPanel onCaseOpened={openCase} />
      ) : error ? (
        <ErrorState message={error} onRetry={reload} />
      ) : loading ? (
        <SkeletonBlock className="h-32" />
      ) : !caseData ? (
        <EmptyState title="Case not found" description="No case exists with that ID." />
      ) : (
        <>
          <CaseStatusPanel caseData={caseData} onUpdated={reload} />
          <div className="grid grid-cols-2 gap-4">
            <CaseNotesPanel caseId={activeCaseId} />
            <CaseEvidencePanel caseId={activeCaseId} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <CaseResolutionPanel caseId={activeCaseId} />
            <CaseDossierPanel caseId={activeCaseId} />
          </div>
        </>
      )}
    </div>
  );
}

const TYPE_ICON = { account: UserRoundSearch, complaint: FileWarning, location: MapPinned } as const;
const TYPE_ROUTE: Record<InvestigationPin["entityType"], (id: string) => string> = {
  account: (id) => analystPath(`/accounts/${id}`),
  complaint: (id) => analystPath(`/complaints/${id}`),
  location: () => analystPath(`/cashout`),
};
const TYPE_LABEL = { account: "Account", complaint: "Complaint", location: "Location" } as const;

export function InvestigationWorkspace() {
  const navigate = useNavigate();
  const { pins, removePin, clearPins } = useWorkspace();

  const columns: InvestigationPin["entityType"][] = ["complaint", "account", "location"];

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="Investigation Workspace"
        title="Investigation Board"
        description="Pinned complaints, accounts, and locations for the case you're actively building. Session-local — not yet persisted to the backend."
        actions={
          pins.length > 0 && (
            <button
              onClick={clearPins}
              className="rounded-sm border border-[color:var(--color-border-strong)] px-3 py-1.5 text-[12px] font-medium text-[color:var(--color-text-secondary)] hover:border-[color:var(--color-critical)] hover:text-[color:var(--color-critical)]"
            >
              Clear board
            </button>
          )
        }
      />

      {pins.length === 0 ? (
        <div className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)]">
          <EmptyState
            title="YOUR INVESTIGATION BOARD IS EMPTY"
            description="Pin complaints, accounts, or locations from their intelligence pages to build a working case file here."
          />
        </div>
      ) : (
        <div className="grid grid-cols-3 gap-4">
          {columns.map((type) => {
            const Icon = TYPE_ICON[type];
            const items = pins.filter((p) => p.entityType === type);
            return (
              <div key={type} className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)]">
                <div className="flex items-center gap-2 border-b border-[color:var(--color-border)] px-4 py-3">
                  <Icon className="h-3.5 w-3.5 text-[color:var(--color-signal)]" strokeWidth={1.75} />
                  <h2 className="text-[12.5px] font-semibold text-[color:var(--color-text-primary)]">{TYPE_LABEL[type]}s</h2>
                  <span className="ml-auto text-[11px] text-[color:var(--color-text-tertiary)]">{items.length}</span>
                </div>
                {items.length === 0 ? (
                  <p className="px-4 py-6 text-center text-[11.5px] text-[color:var(--color-text-tertiary)]">No {TYPE_LABEL[type].toLowerCase()}s pinned yet.</p>
                ) : (
                  <div className="divide-y divide-[color:var(--color-border)]">
                    {items.map((p) => (
                      <div key={p.id} className="group flex items-center gap-2.5 px-4 py-2.5">
                        <button onClick={() => navigate(TYPE_ROUTE[type](p.entityId))} className="min-w-0 flex-1 text-left">
                          <div className="mono-id text-[12.5px] font-medium text-[color:var(--color-signal)]">{p.label}</div>
                          <div className="text-[10.5px] text-[color:var(--color-text-tertiary)]">Pinned {timeAgo(p.pinnedAt)}</div>
                        </button>
                        {p.risk && <RiskBadge risk={p.risk} size="sm" />}
                        <button
                          onClick={() => removePin(p.id)}
                          className="text-[color:var(--color-text-tertiary)] opacity-0 transition-opacity hover:text-[color:var(--color-critical)] group-hover:opacity-100"
                          aria-label="Remove pin"
                        >
                          <PinOff className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      <div className="mt-4 flex items-start gap-2.5 rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)] px-4 py-3">
        <FolderSearch className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[color:var(--color-text-tertiary)]" />
        <p className="text-[11.5px] leading-snug text-[color:var(--color-text-tertiary)]">
          The pinboard above holds pins in local session state only — a separate, session-local working space from the persisted backend Case workflow below.
        </p>
      </div>

      <BackendCaseSection />
    </div>
  );
}
