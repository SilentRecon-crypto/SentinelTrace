import { useMemo, useRef, useState } from "react";
import { ZoomIn, ZoomOut, Maximize2, Waypoints } from "lucide-react";
import clsx from "clsx";
import type { NetworkGraph, NetworkNode, RiskLevel } from "@/types";

const RISK_COLOR: Record<RiskLevel, string> = {
  critical: "var(--color-critical)",
  high: "var(--color-high)",
  medium: "var(--color-medium)",
  low: "var(--color-low)",
};

const TYPE_COLOR: Record<string, string> = {
  victim: "var(--color-text-tertiary)",
  complaint: "var(--color-info)",
  account: "var(--color-signal)",
  location: "var(--color-high)",
};

function layout(graph: NetworkGraph) {
  const layerOf: Record<string, number> = {};
  const nodesByType = { victim: [] as NetworkNode[], complaint: [] as NetworkNode[], account: [] as NetworkNode[], location: [] as NetworkNode[] };
  graph.nodes.forEach((n) => nodesByType[n.type].push(n));

  let layer = 0;
  nodesByType.victim.forEach((n) => (layerOf[n.id] = layer));
  layer += 1;
  nodesByType.complaint.forEach((n) => (layerOf[n.id] = layer));
  layer += 1;
  nodesByType.account.forEach((n, i) => (layerOf[n.id] = layer + i));
  layer += Math.max(1, nodesByType.account.length);
  nodesByType.location.forEach((n) => (layerOf[n.id] = layer));

  const COL_WIDTH = 190;
  const ROW_HEIGHT = 88;
  const positioned: (NetworkNode & { x: number; y: number })[] = [];

  const colGroups: Record<number, NetworkNode[]> = {};
  graph.nodes.forEach((n) => {
    const l = layerOf[n.id];
    (colGroups[l] ??= []).push(n);
  });

  Object.entries(colGroups).forEach(([colStr, nodes]) => {
    const col = Number(colStr);
    nodes.forEach((n, i) => {
      const totalHeight = (nodes.length - 1) * ROW_HEIGHT;
      positioned.push({ ...n, x: 90 + col * COL_WIDTH, y: 160 - totalHeight / 2 + i * ROW_HEIGHT });
    });
  });

  const width = 90 + (layer + 1) * COL_WIDTH;
  return { positioned, width, height: 340 };
}

export function NetworkGraphView({ graph }: { graph: NetworkGraph }) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [tracePath, setTracePath] = useState(false);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const dragging = useRef<{ x: number; y: number } | null>(null);

  const { positioned, width, height } = useMemo(() => layout(graph), [graph]);
  const nodeMap = useMemo(() => Object.fromEntries(positioned.map((n) => [n.id, n])), [positioned]);
  const selectedNode = selectedId ? graph.nodes.find((n) => n.id === selectedId) : null;

  function onPointerDown(e: React.PointerEvent) {
    dragging.current = { x: e.clientX - pan.x, y: e.clientY - pan.y };
  }
  function onPointerMove(e: React.PointerEvent) {
    if (dragging.current) setPan({ x: e.clientX - dragging.current.x, y: e.clientY - dragging.current.y });
  }
  function onPointerUp() {
    dragging.current = null;
  }

  return (
    <div className="relative overflow-hidden rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface)]">
      {/* Toolbar */}
      <div className="absolute left-3 top-3 z-10 flex items-center gap-1 rounded-sm border border-[color:var(--color-border-strong)] bg-[color:var(--color-surface-raised)]/95 p-1 backdrop-blur">
        <button onClick={() => setZoom((z) => Math.min(2, z + 0.15))} className="flex h-7 w-7 items-center justify-center rounded-sm text-[color:var(--color-text-secondary)] hover:bg-[color:var(--color-surface-hover)]">
          <ZoomIn className="h-3.5 w-3.5" />
        </button>
        <button onClick={() => setZoom((z) => Math.max(0.5, z - 0.15))} className="flex h-7 w-7 items-center justify-center rounded-sm text-[color:var(--color-text-secondary)] hover:bg-[color:var(--color-surface-hover)]">
          <ZoomOut className="h-3.5 w-3.5" />
        </button>
        <button
          onClick={() => {
            setZoom(1);
            setPan({ x: 0, y: 0 });
          }}
          className="flex h-7 w-7 items-center justify-center rounded-sm text-[color:var(--color-text-secondary)] hover:bg-[color:var(--color-surface-hover)]"
        >
          <Maximize2 className="h-3.5 w-3.5" />
        </button>
        <div className="mx-1 h-4 w-px bg-[color:var(--color-border)]" />
        <button
          onClick={() => setTracePath((t) => !t)}
          className={clsx(
            "flex items-center gap-1.5 rounded-sm px-2 py-1 text-[11px] font-medium transition-colors",
            tracePath ? "bg-[color:var(--color-signal)] text-[#04191c]" : "text-[color:var(--color-text-secondary)] hover:bg-[color:var(--color-surface-hover)]"
          )}
        >
          <Waypoints className="h-3.5 w-3.5" /> Trace Path
        </button>
      </div>

      {/* Legend */}
      <div className="absolute bottom-3 left-3 z-10 flex items-center gap-3 rounded-sm border border-[color:var(--color-border-strong)] bg-[color:var(--color-surface-raised)]/95 px-2.5 py-1.5 backdrop-blur">
        {Object.entries(TYPE_COLOR).map(([type, color]) => (
          <div key={type} className="flex items-center gap-1.5 text-[10.5px] capitalize text-[color:var(--color-text-secondary)]">
            <span className="h-2 w-2 rounded-full" style={{ background: color }} />
            {type}
          </div>
        ))}
      </div>

      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="h-[400px] w-full cursor-grab active:cursor-grabbing"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerLeave={onPointerUp}
      >
        <g transform={`translate(${pan.x} ${pan.y}) scale(${zoom})`} style={{ transformOrigin: "center" }}>
          {graph.edges.map((edge) => {
            const s = nodeMap[edge.source];
            const t = nodeMap[edge.target];
            if (!s || !t) return null;
            const onPath = edge.onTracePath && tracePath;
            const dim = tracePath && !onPath;
            return (
              <g key={edge.id}>
                <path
                  d={`M ${s.x + 60} ${s.y} C ${s.x + 60 + (t.x - s.x) / 2} ${s.y}, ${t.x - 60 - (t.x - s.x) / 2} ${t.y}, ${t.x - 60} ${t.y}`}
                  fill="none"
                  stroke={onPath ? "var(--color-signal)" : "var(--color-border-strong)"}
                  strokeWidth={onPath ? 2 : 1.2}
                  opacity={dim ? 0.25 : 1}
                  markerEnd="url(#arrow)"
                />
                {edge.amount && !dim && (
                  <text x={(s.x + t.x) / 2} y={(s.y + t.y) / 2 - 8} textAnchor="middle" fontSize="9.5" fill="var(--color-text-tertiary)" fontFamily="var(--font-mono)">
                    ₹{edge.amount.toLocaleString("en-IN")}
                  </text>
                )}
              </g>
            );
          })}

          <defs>
            <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--color-border-strong)" />
            </marker>
          </defs>

          {positioned.map((n) => {
            const isSelected = selectedId === n.id;
            const onPath = tracePath && graph.tracePathNodeIds.includes(n.id);
            const dim = tracePath && !onPath;
            const color = n.risk ? RISK_COLOR[n.risk] : TYPE_COLOR[n.type];
            return (
              <g
                key={n.id}
                transform={`translate(${n.x} ${n.y})`}
                className="cursor-pointer"
                opacity={dim ? 0.3 : 1}
                onClick={() => setSelectedId(n.id)}
              >
                <rect
                  x={-58}
                  y={-22}
                  width={116}
                  height={44}
                  rx={5}
                  fill="var(--color-surface-raised)"
                  stroke={isSelected ? "var(--color-signal)" : color}
                  strokeWidth={isSelected ? 2 : 1.3}
                />
                <circle cx={-46} cy={0} r={4} fill={color} />
                <text x={-36} y={-2} fontSize="11" fontWeight={600} fill="var(--color-text-primary)" fontFamily="var(--font-mono)">
                  {n.label.length > 13 ? n.label.slice(0, 12) + "…" : n.label}
                </text>
                <text x={-36} y={12} fontSize="8.5" fill="var(--color-text-tertiary)" letterSpacing="0.04em">
                  {n.type.toUpperCase()}
                </text>
              </g>
            );
          })}
        </g>
      </svg>

      {selectedNode && (
        <div className="absolute right-3 top-3 z-10 w-[230px] rounded-md border border-[color:var(--color-border-strong)] bg-[color:var(--color-surface-raised)]/97 p-3.5 backdrop-blur">
          <div className="text-[10px] font-semibold uppercase tracking-[0.06em] text-[color:var(--color-text-tertiary)]">Entity</div>
          <div className="mono-id mt-0.5 text-[15px] font-semibold text-[color:var(--color-text-primary)]">{selectedNode.id}</div>
          {selectedNode.risk && (
            <div className="mt-1 text-[11px] font-medium" style={{ color: RISK_COLOR[selectedNode.risk] }}>
              Risk: {selectedNode.risk.toUpperCase()}
            </div>
          )}
          {selectedNode.meta && (
            <div className="mt-2.5 space-y-1.5 border-t border-[color:var(--color-border)] pt-2.5">
              {Object.entries(selectedNode.meta).map(([k, v]) => (
                <div key={k} className="flex items-center justify-between text-[11.5px]">
                  <span className="text-[color:var(--color-text-tertiary)]">{k}</span>
                  <span className="mono-id font-medium text-[color:var(--color-text-primary)]">{v}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
