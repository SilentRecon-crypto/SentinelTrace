import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { analystPath } from "@/routes";
import { ArrowLeft, Network as NetworkIcon, Target } from "lucide-react";
import { useAsync } from "@/hooks/useAsync";
import { getComplaintById, formatComplaintId } from "@/services/complaints";
import { getMuleChainPrediction } from "@/services/predictions";
import { getComplaintGraph, adaptGraphToNetworkGraph } from "@/services/graph";
import { getComplaintRisk, generateComplaintRisk, getComplaintInterventionWindow } from "@/services/risk";
import { generateComplaintAlerts, getComplaintAlerts } from "@/services/alerts";
import { openCaseForAlert, extractCaseIdFromDuplicateMessage } from "@/services/cases";
import { getLocations, getPredictions } from "@/services/api";
import { ApiError } from "@/services/httpClient";
import { RiskBadge } from "@/components/ui/RiskBadge";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { SkeletonBlock } from "@/components/ui/Skeleton";
import { ErrorState, EmptyState } from "@/components/ui/States";
import { NetworkGraphView } from "@/components/network/NetworkGraphView";
import { formatINR, formatSyntheticDay, formatDateTime, formatPct } from "@/utils/format";
import { PinButton } from "@/components/ui/PinButton";
import type { RiskLevel } from "@/types";

// ============================================================
// INTEGRATION STATUS (Slice 3): adds real Graph (/graph), Risk (/risk),
// and Intervention Window (/intervention-window) data. See Slice 1/2
// comments above for the complaint/prediction integration notes, which
// still apply unchanged.
//
// GRAPH: rendered via the EXISTING, UNMODIFIED NetworkGraphView component
// (src/components/network/NetworkGraphView.tsx) — only the DATA feeding it
// is adapted (see src/services/graph.ts). Labeled "Network Intelligence",
// never "Confirmed Mule Chain" — every node/edge here is a transaction
// relationship or a Model A candidate, never a ground-truth assertion.
//
// RISK: the backend has no single complaint-level risk value — RiskScoreOut
// is one row PER CANDIDATE ACCOUNT. The header risk badge therefore stays
// "PENDING" (unchanged from Slice 1/2 — there is genuinely nothing honest
// to put there at complaint level). Real, distinct Model A score / risk
// priority score / risk band are instead shown per-account in the new
// "Risk Assessment" panel below. If no risk has been computed yet, an
// explicit "Generate Risk Assessment" button calls POST /risk — a real,
// user-initiated action, never triggered automatically on page load.
//
// INTERVENTION: shown verbatim from GET /intervention-window, including
// the backend's own `validation_status` (e.g. "synthetic_demo_only") —
// never hidden or reworded. Only exists for the complaint's single
// top-ranked (rank==1) candidate, labeled as such.
//
// ALERTS (Slice 5): GET /complaints/{id}/alerts is auto-fetched (a pure
// read), but generation (POST .../alerts/generate) is only ever triggered
// by the explicit "Generate Alerts" button — never on page load, risk
// fetch, or risk generation. Each alert's `priority_score` is Stage 5's
// own derived value, kept visually and textually distinct from both
// Model A's score (Model A panel above) and the risk priority score
// (Risk Assessment panel above) — never merged or relabeled. "Open
// Investigation" calls the existing Slice 4 case-creation endpoint
// (POST /alerts/{alert_id}/cases, via the same openCaseForAlert() function
// InvestigationWorkspace.tsx already uses — not duplicated) and hands the
// resulting case_id to the EXISTING Investigation Workspace route via a
// `?case=` query param — no new route, App.tsx untouched. A 409 (case
// already exists) surfaces the backend's real message, with the existing
// case_id parsed out of that same message and offered as a one-click
// "Open it" link — never a fabricated ID.
// ============================================================

export function ComplaintDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const complaintId = Number(id);
  const validId = Number.isInteger(complaintId) && complaintId > 0;

  const { data: complaint, loading, error, reload } = useAsync(
    () => (validId ? getComplaintById(complaintId) : Promise.reject(new Error("Invalid complaint ID"))),
    [complaintId]
  );
  const { data: prediction, loading: predictionLoading } = useAsync(
    () => (validId ? getMuleChainPrediction(complaintId) : Promise.resolve(null)),
    [complaintId]
  );
  const { data: graph, loading: graphLoading } = useAsync(
    () => (validId ? getComplaintGraph(complaintId) : Promise.reject(new Error("Invalid complaint ID"))),
    [complaintId]
  );
  const { data: risk, loading: riskLoading, reload: reloadRisk } = useAsync(
    () => (validId ? getComplaintRisk(complaintId) : Promise.resolve(null)),
    [complaintId]
  );
  const { data: intervention, reload: reloadIntervention } = useAsync(
    () => (validId ? getComplaintInterventionWindow(complaintId) : Promise.resolve(null)),
    [complaintId]
  );
  const { data: alertsResponse, loading: alertsLoading, reload: reloadAlerts } = useAsync(
    () => (validId ? getComplaintAlerts(complaintId) : Promise.reject(new Error("Invalid complaint ID"))),
    [complaintId]
  );

  const [generating, setGenerating] = useState(false);
  const [generateError, setGenerateError] = useState<string | null>(null);
  const [generatingAlerts, setGeneratingAlerts] = useState(false);
  const [alertGenerateError, setAlertGenerateError] = useState<string | null>(null);
  const [openingCaseFor, setOpeningCaseFor] = useState<string | null>(null);
  const [caseMessage, setCaseMessage] = useState<{ alertId: string; text: string; existingCaseId?: string } | null>(null);

  // Recalculating risk is DESTRUCTIVE beyond this panel: the backend
  // cascades risk_scores -> alerts -> cases -> case_notes/evidence/
  // resolution (all ON DELETE CASCADE, per Stages 5-8). Any existing
  // alert/case/notes/evidence/resolution for this complaint would be
  // silently deleted by a recalculation. This was previously undisclosed
  // to the analyst — fixed here with an explicit confirmation, and by
  // refreshing the Alerts panel afterward so it can't show stale data
  // that no longer exists on the backend (isRecalculate=false, the first-
  // time "Generate Risk Assessment" path, has nothing downstream yet to
  // lose, so it skips the confirmation).
  async function handleGenerateRisk(isRecalculate: boolean) {
    if (isRecalculate) {
      const confirmed = window.confirm(
        "Recalculating risk will regenerate this complaint's risk scores. Any existing alert, case, notes, evidence, and resolution for this complaint will be deleted as a result (the backend cascades risk → alerts → case). Continue?"
      );
      if (!confirmed) return;
    }
    setGenerating(true);
    setGenerateError(null);
    try {
      await generateComplaintRisk(complaintId);
      reloadRisk();
      reloadIntervention();
      reloadAlerts();
    } catch (err) {
      setGenerateError(err instanceof Error ? err.message : "Risk generation failed.");
    } finally {
      setGenerating(false);
    }
  }

  // Explicit analyst action only — never triggered on page load, on risk
  // fetch, or on risk generation. Bridges Risk Assessment -> Alert (Slice 5).
  async function handleGenerateAlerts() {
    setGeneratingAlerts(true);
    setAlertGenerateError(null);
    try {
      await generateComplaintAlerts(complaintId);
      reloadAlerts();
    } catch (err) {
      setAlertGenerateError(err instanceof Error ? err.message : "Alert generation failed.");
    } finally {
      setGeneratingAlerts(false);
    }
  }

  // Bridges Alert -> Case -> the existing Investigation Workspace route,
  // via a query param (?case=<id>) on the SAME existing "workspace" route —
  // no new route registered, App.tsx untouched.
  async function handleOpenCase(alertId: string) {
    setOpeningCaseFor(alertId);
    setCaseMessage(null);
    try {
      const created = await openCaseForAlert(alertId);
      navigate(analystPath(`/workspace?case=${created.case_id}`));
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        const existingId = extractCaseIdFromDuplicateMessage(err.message);
        setCaseMessage({ alertId, text: err.message, existingCaseId: existingId ?? undefined });
      } else {
        setCaseMessage({ alertId, text: err instanceof Error ? err.message : "Could not open a case for this alert." });
      }
    } finally {
      setOpeningCaseFor(null);
    }
  }

  // Cash-Out Locations panel: unchanged mock data source (Model B does not
  // exist in the backend). getPredictions() falls back to a generic demo
  // pool when the given ID has no linked mock locations, which every real
  // complaint ID hits — this is expected and harmless for a clearly-
  // labeled demo panel.
  const { data: mockPrediction } = useAsync(() => getPredictions(String(complaintId)), [complaintId]);
  const { data: allLocations } = useAsync(getLocations, []);

  if (error || !validId) return <ErrorState message={validId ? error ?? undefined : "Invalid complaint ID"} onRetry={reload} />;
  if (loading || !complaint) {
    return (
      <div className="space-y-4">
        <SkeletonBlock className="h-24" />
        <SkeletonBlock className="h-64" />
      </div>
    );
  }

  const candidates = prediction?.results ?? [];
  const riskByAccount = new Map((risk?.results ?? []).map((r) => [r.account_id, r]));
  const topLocations = (allLocations ?? []).filter((l) => mockPrediction?.locations.some((p) => p.locationId === l.id)).slice(0, 5);
  const networkGraph = graph ? adaptGraphToNetworkGraph(graph) : null;

  return (
    <div className="animate-fade-in space-y-4">
      <button onClick={() => navigate(-1)} className="flex items-center gap-1.5 text-[12px] font-medium text-[color:var(--color-text-tertiary)] hover:text-[color:var(--color-text-secondary)]">
        <ArrowLeft className="h-3.5 w-3.5" /> Back
      </button>

      <div className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)] p-5">
        <div className="flex items-start justify-between">
          <div>
            <div className="mb-1 text-[11px] font-medium uppercase tracking-[0.08em] text-[color:var(--color-signal)]">Complaint Intelligence</div>
            <div className="flex items-center gap-3">
              <h1 className="mono-id text-[22px] font-semibold text-[color:var(--color-text-primary)]">{formatComplaintId(complaint.complaint_id)}</h1>
              <span className="text-[16px] font-semibold text-[color:var(--color-text-primary)]">{formatINR(complaint.fraud_amount)}</span>
              <RiskBadge risk="pending" />
            </div>
            <p className="mt-1 text-[12px] text-[color:var(--color-text-tertiary)]">Filed {formatSyntheticDay(complaint.day)}</p>
          </div>
          <div className="flex items-center gap-2">
            <StatusBadge status="pending" />
            <PinButton entityType="complaint" entityId={String(complaint.complaint_id)} label={formatComplaintId(complaint.complaint_id)} />
            <button
              onClick={() => navigate(analystPath(`/networks?complaint=${complaint.complaint_id}`))}
              className="flex items-center gap-1.5 rounded-sm border border-[color:var(--color-border-strong)] px-3 py-1.5 text-[12px] font-medium text-[color:var(--color-text-secondary)] hover:border-[color:var(--color-signal)] hover:text-[color:var(--color-signal)]"
            >
              <NetworkIcon className="h-3.5 w-3.5" /> Transaction Network
            </button>
          </div>
        </div>
      </div>

      {/* Model A predicted mule-chain — ranked candidates, NOT a confirmed chain */}
      <div className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)] p-4">
        <h2 className="mb-1 text-[13px] font-semibold text-[color:var(--color-text-primary)]">Model A Predicted Mule-Chain</h2>
        <p className="mb-4 text-[11px] text-[color:var(--color-text-tertiary)]">Ranked candidate accounts from Model A — a set of predictions, not a confirmed transaction path.</p>
        {predictionLoading ? (
          <SkeletonBlock className="h-16" />
        ) : candidates.length === 0 ? (
          <p className="py-4 text-[12.5px] text-[color:var(--color-text-tertiary)]">No Model A prediction has been generated yet for this complaint.</p>
        ) : (
          <div className="flex items-center gap-0 overflow-x-auto pb-2">
            {candidates.map((c, i) => (
              <div key={c.candidate_account_id} className="flex items-center">
                <div className="flex min-w-[110px] flex-col items-center gap-1.5 rounded-sm border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-3 py-2.5 text-center">
                  <span className="mono-id text-[12px] font-semibold text-[color:var(--color-text-primary)]">ACC-{c.candidate_account_id}</span>
                  <span className="text-[9.5px] uppercase tracking-wide text-[color:var(--color-text-tertiary)]">Rank #{c.rank}</span>
                </div>
                {i < candidates.length - 1 && <div className="h-px w-8 shrink-0 bg-[color:var(--color-border-strong)]" />}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Network Intelligence — real transaction graph, existing NetworkGraphView component, unmodified */}
      <div className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)] p-4">
        <div className="mb-1 flex items-center justify-between">
          <h2 className="text-[13px] font-semibold text-[color:var(--color-text-primary)]">Network Intelligence</h2>
          {graph?.truncated && (
            <span className="text-[10.5px] text-[color:var(--color-text-tertiary)]">Graph truncated at {graph.node_count} nodes</span>
          )}
        </div>
        <p className="mb-3 text-[11px] text-[color:var(--color-text-tertiary)]">
          Transaction network around this complaint. Highlighted "Trace Path" nodes are Model A candidates, not a confirmed mule chain.
        </p>
        {graphLoading ? (
          <SkeletonBlock className="h-[400px]" />
        ) : !networkGraph || networkGraph.nodes.length === 0 ? (
          <EmptyState title="No graph data" description="No transaction network is available for this complaint." />
        ) : (
          <NetworkGraphView graph={networkGraph} />
        )}
      </div>

      {/* Risk Assessment — real per-candidate risk, Model A score kept distinct from risk priority score/band */}
      <div className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)] p-4">
        <div className="mb-1 flex items-center justify-between">
          <h2 className="text-[13px] font-semibold text-[color:var(--color-text-primary)]">Risk Assessment</h2>
          {risk && (
            <button
              onClick={() => handleGenerateRisk(true)}
              disabled={generating}
              className="rounded-sm border border-[color:var(--color-border-strong)] px-2.5 py-1 text-[11px] font-medium text-[color:var(--color-text-secondary)] hover:border-[color:var(--color-signal)] hover:text-[color:var(--color-signal)] disabled:opacity-50"
            >
              {generating ? "Recalculating…" : "Recalculate"}
            </button>
          )}
        </div>
        <p className="mb-3 text-[11px] text-[color:var(--color-text-tertiary)]">
          Model A score, risk priority score, and risk band are distinct values — shown separately per candidate account, never merged.
        </p>
        {riskLoading ? (
          <SkeletonBlock className="h-16" />
        ) : !risk ? (
          <div className="flex flex-col items-start gap-2 py-2">
            <p className="text-[12.5px] text-[color:var(--color-text-tertiary)]">No risk assessment has been generated yet for this complaint.</p>
            <button
              onClick={() => handleGenerateRisk(false)}
              disabled={generating}
              className="rounded-sm bg-[color:var(--color-signal)] px-3 py-1.5 text-[12px] font-semibold text-[#04191c] hover:opacity-90 disabled:opacity-50"
            >
              {generating ? "Generating…" : "Generate Risk Assessment"}
            </button>
            {generateError && <p className="text-[11px] text-[color:var(--color-critical)]">{generateError}</p>}
          </div>
        ) : (
          <div className="divide-y divide-[color:var(--color-border)]">
            {risk.results.map((r) => (
              <div key={r.account_id} className="flex w-full flex-wrap items-center gap-x-4 gap-y-1 py-2.5">
                <span className="mono-id w-24 text-[12.5px] font-medium text-[color:var(--color-text-primary)]">ACC-{r.account_id}</span>
                <span className="text-[11px] text-[color:var(--color-text-tertiary)]">Model A: <span className="mono-id text-[color:var(--color-text-secondary)]">{formatPct(r.ml_score * 100)}</span></span>
                <span className="text-[11px] text-[color:var(--color-text-tertiary)]">Priority Score: <span className="mono-id text-[color:var(--color-text-secondary)]">{r.priority.value.toFixed(3)}</span></span>
                <RiskBadge risk={r.priority.level as RiskLevel} size="sm" />
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Alerts — Stage 5, explicit generation only. Bridges Risk -> Case (Slice 5). */}
      <div className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)] p-4">
        <div className="mb-1 flex items-center justify-between">
          <h2 className="text-[13px] font-semibold text-[color:var(--color-text-primary)]">Alerts</h2>
          <button
            onClick={handleGenerateAlerts}
            disabled={generatingAlerts}
            className="rounded-sm bg-[color:var(--color-signal)] px-3 py-1.5 text-[12px] font-semibold text-[#04191c] hover:opacity-90 disabled:opacity-50"
          >
            {generatingAlerts ? "Generating…" : "Generate Alerts"}
          </button>
        </div>
        <p className="mb-3 text-[11px] text-[color:var(--color-text-tertiary)]">
          Alert priority score is Stage 5's own derived value — distinct from Model A's score and the risk priority score above.
        </p>
        {alertGenerateError && <p className="mb-2 text-[11px] text-[color:var(--color-critical)]">{alertGenerateError}</p>}
        {alertsLoading ? (
          <SkeletonBlock className="h-16" />
        ) : !alertsResponse || alertsResponse.results.length === 0 ? (
          <p className="py-2 text-[12.5px] text-[color:var(--color-text-tertiary)]">No alerts generated yet for this complaint.</p>
        ) : (
          <div className="divide-y divide-[color:var(--color-border)]">
            {alertsResponse.results.map((a) => (
              <div key={a.alert_id} className="flex flex-wrap items-center gap-x-4 gap-y-1.5 py-2.5">
                <span className="mono-id text-[12px] font-medium text-[color:var(--color-text-primary)]">{a.alert_type.replace(/_/g, " ")}</span>
                <RiskBadge risk={a.severity as RiskLevel} size="sm" />
                <StatusBadge status={a.status} />
                <span className="text-[11px] text-[color:var(--color-text-tertiary)]">Alert Priority: <span className="mono-id text-[color:var(--color-text-secondary)]">{a.priority_score.toFixed(3)}</span></span>
                <span className="text-[11px] text-[color:var(--color-text-tertiary)]">Risk Priority: <span className="mono-id text-[color:var(--color-text-secondary)]">{a.risk_priority_value.toFixed(3)}</span></span>
                <span className="text-[10.5px] text-[color:var(--color-text-tertiary)]">{formatDateTime(a.created_at)}</span>
                <button
                  onClick={() => handleOpenCase(a.alert_id)}
                  disabled={openingCaseFor === a.alert_id}
                  className="ml-auto rounded-sm border border-[color:var(--color-border-strong)] px-2.5 py-1 text-[11px] font-medium text-[color:var(--color-text-secondary)] hover:border-[color:var(--color-signal)] hover:text-[color:var(--color-signal)] disabled:opacity-50"
                >
                  {openingCaseFor === a.alert_id ? "Opening…" : "Open Investigation"}
                </button>
                {caseMessage?.alertId === a.alert_id && (
                  <div className="w-full rounded-sm border border-[color:var(--color-border-strong)] px-3 py-2 text-[11px] text-[color:var(--color-text-secondary)]">
                    {caseMessage.text}
                    {caseMessage.existingCaseId && (
                      <button
                        onClick={() => navigate(analystPath(`/workspace?case=${caseMessage.existingCaseId}`))}
                        className="ml-2 font-medium text-[color:var(--color-signal)] hover:underline"
                      >
                        Open it
                      </button>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* Model A candidates — detail list */}
        <div className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)]">
          <div className="border-b border-[color:var(--color-border)] px-4 py-3">
            <h2 className="text-[13px] font-semibold text-[color:var(--color-text-primary)]">Model A Candidates</h2>
          </div>
          {candidates.length === 0 ? (
            <p className="px-4 py-4 text-[12px] text-[color:var(--color-text-tertiary)]">No candidates available.</p>
          ) : (
            <div className="divide-y divide-[color:var(--color-border)]">
              {candidates.map((c) => {
                const accountRisk = riskByAccount.get(c.candidate_account_id);
                return (
                  <div key={c.candidate_account_id} className="flex w-full items-center gap-3 px-4 py-2.5">
                    <span className="mono-id w-6 text-[11px] text-[color:var(--color-text-tertiary)]">#{c.rank}</span>
                    <span className="mono-id flex-1 text-[12.5px] font-medium text-[color:var(--color-text-primary)]">ACC-{c.candidate_account_id}</span>
                    <span className="text-[11px] text-[color:var(--color-text-tertiary)]">{c.hop_distance} hop{c.hop_distance === 1 ? "" : "s"}</span>
                    <span className="mono-id text-[13px] font-semibold text-[color:var(--color-text-primary)]">{(c.model_score * 100).toFixed(1)}%</span>
                    {accountRisk && <RiskBadge risk={accountRisk.priority.level as RiskLevel} size="sm" />}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Predicted cash-out locations — DEMO DATA, Model B not yet integrated */}
        <div className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)]">
          <div className="flex items-center justify-between border-b border-[color:var(--color-border)] px-4 py-3">
            <div className="flex items-center gap-2">
              <h2 className="text-[13px] font-semibold text-[color:var(--color-text-primary)]">Predicted Cash-Out Locations</h2>
              <span className="rounded-[3px] border border-[color:var(--color-border-strong)] px-1.5 py-0.5 text-[9.5px] font-medium uppercase tracking-wide text-[color:var(--color-text-tertiary)]">
                Demo Data
              </span>
            </div>
            <Target className="h-3.5 w-3.5 text-[color:var(--color-text-tertiary)]" />
          </div>
          <div className="divide-y divide-[color:var(--color-border)]">
            {topLocations.map((l, i) => (
              <button
                key={l.id}
                onClick={() => navigate(analystPath("/cashout"))}
                className="flex w-full items-center gap-3 px-4 py-2.5 text-left transition-colors hover:bg-[color:var(--color-surface-hover)]"
              >
                <span className="mono-id w-5 text-[11px] text-[color:var(--color-text-tertiary)]">#{i + 1}</span>
                <div className="min-w-0 flex-1">
                  <div className="mono-id text-[12.5px] font-medium text-[color:var(--color-text-primary)]">{l.id}</div>
                  <div className="text-[11px] text-[color:var(--color-text-tertiary)]">{l.city}, {l.state}</div>
                </div>
                <span className="mono-id text-[13px] font-semibold text-[color:var(--color-text-primary)]">{l.predictionScore.toFixed(1)}%</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Intervention Window — real backend data, only for the top-ranked candidate */}
      <div className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)] p-4">
        <h2 className="mb-1 text-[13px] font-semibold text-[color:var(--color-text-primary)]">Intervention Window</h2>
        <p className="mb-3 text-[11px] text-[color:var(--color-text-tertiary)]">Only computed for the complaint's top-ranked (rank 1) candidate account.</p>
        {!intervention ? (
          <p className="py-2 text-[12.5px] text-[color:var(--color-text-tertiary)]">No intervention window has been computed yet for this complaint.</p>
        ) : (
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
            <div>
              <div className="text-[10.5px] uppercase tracking-wide text-[color:var(--color-text-tertiary)]">Account</div>
              <div className="mono-id text-[13px] font-medium text-[color:var(--color-text-primary)]">ACC-{intervention.account_id}</div>
            </div>
            <div>
              <div className="text-[10.5px] uppercase tracking-wide text-[color:var(--color-text-tertiary)]">Estimated Window</div>
              <div className="mono-id text-[13px] font-medium text-[color:var(--color-text-primary)]">{intervention.estimated_window_minutes} min</div>
            </div>
            <div>
              <div className="text-[10.5px] uppercase tracking-wide text-[color:var(--color-text-tertiary)]">Urgency</div>
              <RiskBadge risk={intervention.urgency as RiskLevel} size="sm" />
            </div>
            <div>
              <div className="text-[10.5px] uppercase tracking-wide text-[color:var(--color-text-tertiary)]">Predicted Cash-Out Time</div>
              <div className="mono-id text-[13px] font-medium text-[color:var(--color-text-primary)]">{formatDateTime(intervention.predicted_cashout_time)}</div>
            </div>
            <div className="w-full">
              <div className="text-[10.5px] uppercase tracking-wide text-[color:var(--color-text-tertiary)]">Rationale</div>
              <p className="text-[12px] text-[color:var(--color-text-secondary)]">{intervention.rationale}</p>
            </div>
            <div className="w-full text-[10.5px] text-[color:var(--color-text-tertiary)]">
              Validation status: <span className="mono-id">{intervention.validation_status}</span> — method: <span className="mono-id">{intervention.method}</span>
            </div>
          </div>
        )}
      </div>

      {/* Investigation summary — no backend field exists yet */}
      <div className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)] p-4">
        <h2 className="mb-2 text-[13px] font-semibold text-[color:var(--color-text-primary)]">Investigation Summary</h2>
        <p className="text-[12.5px] leading-relaxed text-[color:var(--color-text-secondary)]">No investigator summary available for this complaint yet.</p>
      </div>
    </div>
  );
}
