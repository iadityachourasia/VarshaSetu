"use client";

import { useEffect, useRef, useState } from "react";
import { Map as MapLibreMap, setWorkerUrl } from "maplibre-gl";
import { onlineStyle, type GeographicStyle } from "@/lib/maps/basemap";

/** Frame that always shows the whole of India with some margin; the inset is a locator, never a data view. */
const INDIA_FRAME: [[number, number], [number, number]] = [[62, 3], [100, 40]];

/**
 * A small whole-India locator with the data domain of the main map outlined, so the extent of the model box is never mistaken for the extent of the
 * country. It is non-interactive, has no labels and no data, and is simply omitted when the basemap cannot be reached (an offline blank would say nothing).
 */
export function LocatorInset({ bounds, theme }: { bounds: [number, number, number, number]; theme: GeographicStyle }) {
  const element = useRef<HTMLDivElement>(null);
  const [available, setAvailable] = useState(true);
  const boundsKey = bounds.join(",");
  useEffect(() => {
    const container = element.current;
    if (!container) return;
    let map: MapLibreMap | null = null;
    let canceled = false;
    onlineStyle(theme).then((style) => {
      if (canceled || !element.current) return;
      setWorkerUrl("/maplibre-gl-worker.mjs");
      map = new MapLibreMap({ container, style, bounds: INDIA_FRAME, fitBoundsOptions: { padding: 2, duration: 0 }, interactive: false, attributionControl: false, fadeDuration: 0 });
      const [west, south, east, north] = boundsKey.split(",").map(Number);
      map.on("style.load", () => {
        if (!map) return;
        for (const layer of map.getStyle().layers) if (layer.type === "symbol") map.setLayoutProperty(layer.id, "visibility", "none");
        map.addSource("locator-box", { type: "geojson", data: { type: "Feature", properties: {}, geometry: { type: "Polygon", coordinates: [[[west, south], [east, south], [east, north], [west, north], [west, south]]] } } });
        map.addLayer({ id: "locator-box-fill", type: "fill", source: "locator-box", paint: { "fill-color": "#e6a854", "fill-opacity": 0.35 } });
        map.addLayer({ id: "locator-box-line", type: "line", source: "locator-box", paint: { "line-color": "#c27a1d", "line-width": 1.6 } });
        container.dataset.locatorReady = "true";
      });
    }).catch(() => { if (!canceled) setAvailable(false); });
    return () => { canceled = true; map?.remove(); };
  }, [boundsKey, theme]);
  if (!available) return null;
  return <div className="locator-inset" role="img" aria-label={`Locator: the highlighted box, ${bounds[1]} to ${bounds[3]} degrees north and ${bounds[0]} to ${bounds[2]} degrees east, is the data domain within India`}>
    <div ref={element} className="locator-canvas" />
    <span className="locator-caption">Data domain</span>
  </div>;
}
