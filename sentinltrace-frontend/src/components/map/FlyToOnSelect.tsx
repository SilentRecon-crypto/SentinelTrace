import { useEffect, useRef } from "react";
import { useMap } from "react-leaflet";

export function FlyToOnSelect({ lat, lng, zoom = 11 }: { lat: number | null; lng: number | null; zoom?: number }) {
  const map = useMap();
  const firstRun = useRef(true);

  useEffect(() => {
    if (lat == null || lng == null) return;
    // Skip the animated fly-in on initial mount so the map opens on the
    // full-India view instead of immediately jumping to the first selection.
    if (firstRun.current) {
      firstRun.current = false;
      return;
    }
    map.flyTo([lat, lng], Math.max(map.getZoom(), zoom), { duration: 0.7 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lat, lng]);

  return null;
}
