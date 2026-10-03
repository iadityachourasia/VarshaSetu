"use client";

import { useEffect, useRef, useState } from "react";
import { Map as MapLibreMap, ScaleControl, setWorkerUrl, type GeoJSONSource, type LngLatBoundsLike } from "maplibre-gl";
import type { FeatureCollection } from "geojson";
import { offlineStyle, onlineStyle, type BasemapState, type GeographicStyle } from "@/lib/maps/basemap";
import { readableGeographyStyle } from "@/lib/maps/label-layers";
import { installMapChrome } from "@/lib/maps/chrome";

type Options = {
  element: React.RefObject<HTMLDivElement | null>;
  bounds: [number, number, number, number];
  geometry?: FeatureCollection;
  geographicStyle: GeographicStyle;
  onStyleReady: (map: MapLibreMap) => void;
  onReady?: (map: MapLibreMap | null) => void;
};

export function mapBounds(bounds: [number, number, number, number]): LngLatBoundsLike {
  return [[bounds[0], bounds[1]], [bounds[2], bounds[3]]];
}

export function useWeatherMap({ element, bounds, geometry, geographicStyle, onStyleReady, onReady }: Options) {
  const mapRef = useRef<MapLibreMap | null>(null);
  const latest = useRef({ geometry, onStyleReady, onReady, dark: geographicStyle === "dark" });
  const [status, setStatus] = useState<BasemapState>("loading");
  const boundsRef = useRef(bounds);
  useEffect(() => { latest.current = { geometry, onStyleReady, onReady, dark: geographicStyle === "dark" }; }, [geometry, onStyleReady, onReady, geographicStyle]);

  useEffect(() => {
    if (!element.current) return;
    setWorkerUrl("/maplibre-gl-worker.mjs");
    const map = new MapLibreMap({
      container: element.current,
      style: offlineStyle(geographicStyle, latest.current.geometry),
      bounds: mapBounds(boundsRef.current),
      fitBoundsOptions: { padding: 14 },
      attributionControl: false,
      dragRotate: false, pitchWithRotate: false, touchPitch: false,
      minZoom: 3,
    });
    // The current public Dark style references a city-marker sprite absent
    // from its delivered sprite sheet. Supply only that cartographic marker;
    // this does not affect science rasters, values or district geometry.
    map.setMissingStyleImageResolver((id) => {
      if (id !== "circle-11" || map.hasImage(id)) return;
      const size = 11;
      const pixels = new Uint8ClampedArray(size * size * 4);
      for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
        if ((x - 5) ** 2 + (y - 5) ** 2 > 16) continue;
        const offset = (y * size + x) * 4;
        pixels[offset] = 176; pixels[offset + 1] = 187; pixels[offset + 2] = 190; pixels[offset + 3] = 255;
      }
      map.addImage(id, new ImageData(pixels, size, size));
    });
    mapRef.current = map;
    latest.current.onReady?.(map);
    map.addControl(new ScaleControl({ maxWidth: 88, unit: "metric" }), "bottom-left");
    map.on("style.load", () => {
      latest.current.onStyleReady(map);
      try { installMapChrome(map, boundsRef.current, latest.current.dark); } catch { /* furniture only: a failure must never block the science layers */ }
    });
    return () => { latest.current.onReady?.(null); map.remove(); mapRef.current = null; };
    // The map instance intentionally survives case and setting changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    let canceled = false;
    let errors = 0;
    let offlineApplied = false;
    setStatus("loading");
    const fallback = () => {
      if (canceled || offlineApplied) return;
      offlineApplied = true;
      setStatus("offline");
      map.getContainer().dataset.ready = "false";
      map.setStyle(offlineStyle(geographicStyle, latest.current.geometry), { diff: false });
    };
    const tileError = () => {
      errors += 1;
      if (errors >= 3) fallback();
    };
    const onOffline = () => fallback();
    map.on("error", tileError);
    window.addEventListener("offline", onOffline);
    if (navigator.onLine === false) {
      fallback();
    } else {
      onlineStyle(geographicStyle).then((style) => {
        if (canceled) return;
        if (offlineApplied) return;
        errors = 0;
        map.getContainer().dataset.ready = "false";
        map.once("style.load", () => { if (!canceled && !offlineApplied) setStatus("online"); });
        map.setStyle(readableGeographyStyle(style, geographicStyle), { diff: false });
      }).catch(fallback);
    }
    return () => { canceled = true; map.off("error", tileError); window.removeEventListener("offline", onOffline); };
  }, [geographicStyle]);

  useEffect(() => {
    const source = mapRef.current?.getSource("offline-districts") as GeoJSONSource | undefined;
    if (source && geometry) source.setData(geometry);
  }, [geometry, status]);

  return { mapRef, status };
}
