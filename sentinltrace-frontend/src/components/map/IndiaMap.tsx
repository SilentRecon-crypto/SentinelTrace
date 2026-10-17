import { useEffect, useMemo, useState } from "react";
import { MapContainer, TileLayer, Marker, Tooltip, GeoJSON } from "react-leaflet";
import L from "leaflet";
import { AlertTriangle } from "lucide-react";
import type { GeoJsonObject } from "geojson";
import type { LatLngBoundsExpression } from "leaflet";
import type { Location, RiskLevel } from "@/types";
import { MapControls } from "@/components/map/MapControls";
import { FlyToOnSelect } from "@/components/map/FlyToOnSelect";

// Bounding box roughly covering mainland India + islands, used both as the
// map's initial viewport and as the "Recenter India" target.
const INDIA_BOUNDS: LatLngBoundsExpression = [
  [6.5, 66.5],
  [37.5, 98.5],
];
const INDIA_CENTER: [number, number] = [22.9734, 80.6569];

const RISK_RANK: Record<RiskLevel, number> = { critical: 3, high: 2, medium: 1, low: 0 };

// CARTO's basemap tile endpoints require a free client-side API key (see
// https://carto.com/basemaps/apikey). This is a public, rate-limited,
// domain-restrictable key by design — not a secret — so it is read from
// a Vite env var rather than ever being written into source.
const CARTO_API_KEY = import.meta.env.VITE_CARTO_API_KEY;
const CARTO_TILE_URL = `https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png?key=${CARTO_API_KEY}`;

function buildIcon(risk: RiskLevel, rank: number, selected: boolean) {
  const showRank = rank <= 3;
  const html = `
    <div class="st-marker risk-${risk} ${selected ? "is-selected" : ""}">
      ${showRank ? `<div class="st-marker-rank">#${rank}</div>` : ""}
      <div class="st-marker-glow"></div>
      ${risk === "critical" ? '<div class="st-marker-pulse"></div>' : ""}
      <div class="st-marker-ring"></div>
      <div class="st-marker-dot"></div>
    </div>`;
  return L.divIcon({
    html,
    className: "",
    iconSize: [24, 24],
    iconAnchor: [12, 12],
  });
}

function MapConfigError() {
  return (
    <div className="flex h-[460px] flex-col items-center justify-center gap-3 rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-6 text-center">
      <AlertTriangle className="h-6 w-6 text-[color:var(--color-high)]" strokeWidth={1.75} />
      <div>
        <p className="text-[13px] font-medium text-[color:var(--color-text-primary)]">Map configuration missing</p>
        <p className="mt-1 max-w-sm text-[12px] leading-snug text-[color:var(--color-text-tertiary)]">
          Set <code className="mono-id rounded-[3px] bg-[color:var(--color-surface-hover)] px-1 py-0.5">VITE_CARTO_API_KEY</code> in{" "}
          <code className="mono-id rounded-[3px] bg-[color:var(--color-surface-hover)] px-1 py-0.5">.env.local</code>, then restart the dev server.
        </p>
        <p className="mt-2 text-[11px] text-[color:var(--color-text-tertiary)]">
          Get a free key at{" "}
          <a href="https://carto.com/basemaps/apikey" target="_blank" rel="noreferrer" className="text-[color:var(--color-signal)] hover:underline">
            carto.com/basemaps/apikey
          </a>
        </p>
      </div>
    </div>
  );
}

export function IndiaMap({ locations, selectedId, onSelect }: { locations: Location[]; selectedId: string | null; onSelect: (id: string) => void }) {
  const [stateBoundaries, setStateBoundaries] = useState<GeoJsonObject | null>(null);
  const selected = locations.find((l) => l.id === selectedId) ?? null;

  useEffect(() => {
    let active = true;
    fetch("/geo/india-states.geojson")
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (active && data) setStateBoundaries(data);
      })
      .catch(() => {
        /* Boundary reference layer is decorative — fail silently if unavailable */
      });
    return () => {
      active = false;
    };
  }, []);

  // Render highest-risk / highest-rank markers last so they sit on top when
  // locations overlap at low zoom levels.
  const sortedLocations = useMemo(
    () => [...locations].sort((a, b) => RISK_RANK[a.risk] - RISK_RANK[b.risk] || b.rank - a.rank),
    [locations]
  );

  if (!CARTO_API_KEY) {
    return <MapConfigError />;
  }

  return (
    <div className="relative overflow-hidden rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface)]">
      <MapContainer
        bounds={INDIA_BOUNDS}
        center={INDIA_CENTER}
        zoom={5}
        minZoom={4}
        maxZoom={13}
        maxBounds={[
          [0, 55],
          [42, 108],
        ]}
        maxBoundsViscosity={0.5}
        zoomControl={false}
        attributionControl={true}
        className="h-[460px] w-full"
        style={{ background: "var(--color-surface)" }}
      >
        <TileLayer
          url={CARTO_TILE_URL}
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
          subdomains="abcd"
        />

        {stateBoundaries && (
          <GeoJSON
            data={stateBoundaries}
            style={{
              color: "var(--color-border-strong)",
              weight: 0.8,
              opacity: 0.55,
              fillOpacity: 0,
            }}
            interactive={false}
          />
        )}

        {sortedLocations.map((l) => (
          <Marker
            key={l.id}
            position={[l.lat, l.lng]}
            icon={buildIcon(l.risk, l.rank, l.id === selectedId)}
            eventHandlers={{ click: () => onSelect(l.id) }}
          >
            <Tooltip direction="top" offset={[0, -14]} opacity={1} className="st-map-tooltip">
              <div className="mono-id font-semibold">{l.id}</div>
              <div>{l.city}</div>
              <div className="flex items-center gap-1.5">
                <span className="capitalize">{l.risk}</span>
                <span>&middot;</span>
                <span>{l.predictionScore.toFixed(1)}%</span>
              </div>
            </Tooltip>
          </Marker>
        ))}

        <FlyToOnSelect lat={selected?.lat ?? null} lng={selected?.lng ?? null} />
        <MapControls homeBounds={INDIA_BOUNDS} />
      </MapContainer>

      <div className="pointer-events-none absolute bottom-3 left-3 z-[1000] flex items-center gap-3 rounded-sm border border-[color:var(--color-border-strong)] bg-[color:var(--color-surface-raised)]/95 px-2.5 py-1.5 backdrop-blur">
        {(["critical", "high", "medium", "low"] as RiskLevel[]).map((r) => (
          <div key={r} className={`flex items-center gap-1.5 text-[10.5px] capitalize text-[color:var(--color-text-secondary)]`}>
            <span className={`h-2 w-2 rounded-full risk-dot-${r}`} style={{ background: `var(--color-${r})` }} />
            {r}
          </div>
        ))}
      </div>
    </div>
  );
}
