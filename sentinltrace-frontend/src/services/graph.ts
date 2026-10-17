// ============================================================
// Real backend transaction graph — GET /api/v1/complaints/{id}/graph
//
// adaptGraphToNetworkGraph() is the "small adapter/transformer" this
// integration slice calls for: it maps the backend's ComplaintGraphResponse
// onto the EXISTING, UNCHANGED src/components/network/NetworkGraphView's
// expected `NetworkGraph` shape, so that component itself needs zero
// modification. See its inline comments for exactly what is and isn't
// derived, and why.
// ============================================================
import type { NetworkEdge, NetworkGraph, NetworkNode } from "@/types";
import type { BackendComplaintGraph } from "@/services/backendTypes";
import { http } from "@/services/httpClient";

export async function getComplaintGraph(complaintId: number): Promise<BackendComplaintGraph> {
  return http.get<BackendComplaintGraph>(`/api/v1/complaints/${complaintId}/graph`);
}

/**
 * Every backend graph node is an account (there is no separate victim/
 * complaint/location node type in the real data — that was a mock-only
 * multi-tier concept), so every node maps to NetworkNode.type = "account".
 * `risk` is deliberately left unset here: coloring a node by risk would
 * require a classified risk LEVEL, which does not exist without a
 * separate Stage 4 risk lookup (and even then is per-candidate, not
 * universally available for every graph node) — not fabricated here.
 *
 * "Position" in `meta` ("Root Account" / "Candidate — Rank N" /
 * "Intermediate Hop") is derived only from the backend's own real
 * `is_root`/`is_candidate`/`prediction_rank` booleans — never from
 * `chain`, `acc_type`, or any synthetic label. Named "Position", not
 * "Role", specifically to avoid any resemblance to the forbidden
 * synthetic-role-label concept.
 *
 * The existing "Trace Path" toggle (already built into NetworkGraphView,
 * unmodified here) is repurposed to highlight Model A's CANDIDATE nodes
 * (`is_candidate === true`) and the edges directly between them — a real,
 * inference-time signal — NOT a confirmed mule chain. This is why the
 * panel using this data is labeled "Network Intelligence" in
 * ComplaintDetail.tsx, never "Confirmed Mule Chain".
 *
 * KNOWN LAYOUT LIMITATION (disclosed, not silently accepted): because
 * NetworkGraphView.tsx lays out each node of a given `type` in its own
 * column, and every real node here shares the single "account" type, a
 * complaint with many candidates renders as one wide horizontal row
 * rather than the tiered victim→account→location layout the mock data
 * produced. Fixing this would mean modifying NetworkGraphView.tsx's
 * layout logic, which is out of scope for this slice (no redesign of the
 * existing visual component).
 */
export function adaptGraphToNetworkGraph(raw: BackendComplaintGraph): NetworkGraph {
  const nodes: NetworkNode[] = raw.nodes.map((n) => ({
    id: String(n.account_id),
    type: "account",
    label: `ACC-${n.account_id}`,
    meta: {
      Depth: n.depth,
      Position: n.is_root ? "Root Account" : n.is_candidate ? `Candidate — Rank ${n.prediction_rank ?? "?"}` : "Intermediate Hop",
      ...(n.is_candidate && n.model_score != null ? { "Model A Score": `${(n.model_score * 100).toFixed(1)}%` } : {}),
    },
  }));

  const candidateIds = new Set(raw.nodes.filter((n) => n.is_candidate).map((n) => String(n.account_id)));

  const edges: NetworkEdge[] = raw.edges.map((e, i) => ({
    id: `edge-${e.src_account_id}-${e.dst_account_id}-${i}`,
    source: String(e.src_account_id),
    target: String(e.dst_account_id),
    type: "transaction",
    amount: e.total_amount,
    onTracePath: candidateIds.has(String(e.src_account_id)) && candidateIds.has(String(e.dst_account_id)),
  }));

  return {
    complaintId: String(raw.complaint_id),
    nodes,
    edges,
    tracePathNodeIds: Array.from(candidateIds),
  };
}
