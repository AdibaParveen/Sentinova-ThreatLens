"use client";

import { useEffect, useRef } from "react";

export type MapPoint = {
  value: string;
  lat: number | null;
  lon: number | null;
  country?: string | null;
  severity: number;
  type?: string;
};

export function ThreatMap({ points }: { points: MapPoint[] }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    let map: import("leaflet").Map | null = null;
    (async () => {
      const L = await import("leaflet");
      if (typeof document !== "undefined") {
  const cssId = "leaflet-css";

  if (!document.getElementById(cssId)) {
    const link = document.createElement("link");
    link.id = cssId;
    link.rel = "stylesheet";
    link.href = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
    document.head.appendChild(link);
  }
}
      if (!ref.current || cancelled) return;
      map = L.map(ref.current, { worldCopyJump: true }).setView([22, 12], 2);
      L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
        attribution: "&copy; OpenStreetMap &copy; CARTO",
      }).addTo(map);
      points
        .filter((p) => p.lat != null && p.lon != null)
        .forEach((p) => {
          const color = p.severity >= 75 ? "#e5484d" : p.severity >= 50 ? "#f76808" : p.severity >= 25 ? "#f5d90a" : "#30a46c";
          L.circleMarker([p.lat as number, p.lon as number], {
            radius: 6 + Math.min(8, p.severity / 20),
            color,
            fillColor: color,
            fillOpacity: 0.75,
            weight: 1,
          })
            .bindPopup(`<strong>${p.value}</strong><br/>${p.country || "Unknown"} · score ${p.severity}`)
            .addTo(map!);
        });
    })();
    return () => {
      cancelled = true;
      map?.remove();
    };
  }, [points]);

  return <div ref={ref} className="h-[480px] w-full overflow-hidden rounded-lg border border-white/10" />;
}
