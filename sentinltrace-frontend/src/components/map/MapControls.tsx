import { ZoomIn, ZoomOut, LocateFixed } from "lucide-react";
import { useMap } from "react-leaflet";
import type { LatLngBoundsExpression } from "leaflet";

export function MapControls({ homeBounds }: { homeBounds: LatLngBoundsExpression }) {
  const map = useMap();

  return (
    <div className="leaflet-top leaflet-right !top-3 !right-3">
      <div className="leaflet-control flex flex-col gap-1 rounded-sm border border-[color:var(--color-border-strong)] bg-[color:var(--color-surface-raised)]/95 p-1 backdrop-blur">
        <button
          onClick={() => map.zoomIn()}
          className="flex h-7 w-7 items-center justify-center rounded-sm text-[color:var(--color-text-secondary)] hover:bg-[color:var(--color-surface-hover)]"
          aria-label="Zoom in"
          title="Zoom in"
        >
          <ZoomIn className="h-3.5 w-3.5" />
        </button>
        <button
          onClick={() => map.zoomOut()}
          className="flex h-7 w-7 items-center justify-center rounded-sm text-[color:var(--color-text-secondary)] hover:bg-[color:var(--color-surface-hover)]"
          aria-label="Zoom out"
          title="Zoom out"
        >
          <ZoomOut className="h-3.5 w-3.5" />
        </button>
        <div className="h-px w-full bg-[color:var(--color-border)]" />
        <button
          onClick={() => map.flyToBounds(homeBounds, { padding: [24, 24], duration: 0.6 })}
          className="flex h-7 w-7 items-center justify-center rounded-sm text-[color:var(--color-text-secondary)] hover:bg-[color:var(--color-surface-hover)]"
          aria-label="Recenter India"
          title="Recenter India"
        >
          <LocateFixed className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}
