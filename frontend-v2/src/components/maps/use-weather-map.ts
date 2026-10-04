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
  /** The view the map opens on and returns to on reset: the data region. Defaults to `bounds`, which stays the domain the map furniture outlines. */
  fitBounds?: [number, number, number, number];
  onStyleReady: (map: MapLibreMap) => void;
  onReady?: (map: MapLibreMap | null) => void;
};

export function mapBounds(bounds: [number, number, number, number]): LngLatBoundsLike {
  return [[bounds[0], bounds[1]], [bounds[2], bounds[3]]];
}

/** Padding, in pixels, between the data region and the map edge when a map is fitted. */
export const FIT_PADDING = 8;
const fitTargets = new WeakMap<MapLibreMap, [number, number, number, number]>();

/** Beyond this share of empty width a panel counts as wide; there the region is centred and may lose up to WIDE_PANEL_TRIM of its height. */
const WIDE_PANEL_SLACK = 0.35;
const WIDE_PANEL_TRIM = 0.15;

/**
 * Point the camera so the whole data region is shown with no gap along its limiting side: the region is scaled to touch the panel edges in one direction
 * (top and bottom for these tall regions), and any spare width is pushed to the west, where it falls on the Arabian Sea, so the east edge of the data meets
 * the right edge of the panel. Nothing in the region is cropped. Spare height (a panel taller than the region) is split evenly. Wide panels: see WIDE_PANEL_SLACK.
 */
export function fillCamera(map: MapLibreMap, bounds: [number, number, number, number]) {
  const container = map.getContainer();
  const width = container.clientWidth, height = container.clientHeight;
  const southWest = map.project([bounds[0], bounds[1]]), northEast = map.project([bounds[2], bounds[3]]);
  const regionWidth = Math.abs(northEast.x - southWest.x), regionHeight = Math.abs(southWest.y - northEast.y);
  if (!width || !height || !regionWidth || !regionHeight) { map.fitBounds(mapBounds(bounds), { padding: FIT_PADDING, duration: 0 }); return; }
  const contain = Math.min(width / regionWidth, height / regionHeight);
  const slack = 1 - (regionWidth * contain) / width;
  // A panel much wider than the region (Extreme Rain, district maps) would leave a large empty band on one side: keep the region centred there,
  // and trim at most WIDE_PANEL_TRIM of its height to narrow the bands. Comparison panels keep the whole region, east-aligned.
  const wide = slack > WIDE_PANEL_SLACK;
  const scale = wide ? Math.min(Math.max(width / regionWidth, height / regionHeight), contain / (1 - WIDE_PANEL_TRIM)) : contain;
  // Screen centre in current-zoom pixels.
  const centerX = !wide && slack * width > 1 ? Math.max(northEast.x, southWest.x) - width / 2 / scale : (southWest.x + northEast.x) / 2;
  const centerY = (southWest.y + northEast.y) / 2;
  map.jumpTo({ center: map.unproject([centerX, centerY]), zoom: map.getZoom() + Math.log2(scale) });
}

/** Return a map to the data region it registered (its reset view); `fallback` is used for a map that registered none. */
export function fitToData(map: MapLibreMap, fallback?: [number, number, number, number]) {
  const target = fitTargets.get(map) ?? fallback;
  if (target) fillCamera(map, target);
}

export function useWeatherMap({ element, bounds, fitBounds, geometry, geographicStyle, onStyleReady, onReady }: Options) {
  const mapRef = useRef<MapLibreMap | null>(null);
  const latest = useRef({ geometry, onStyleReady, onReady, dark: geographicStyle === "dark" });
  const [status, setStatus] = useState<BasemapState>("loading");
  const boundsRef = useRef(bounds);
  const fitRef = useRef(fitBounds ?? bounds);
  useEffect(() => { latest.current = { geometry, onStyleReady, onReady, dark: geographicStyle === "dark" }; }, [geometry, onStyleReady, onReady, geographicStyle]);

  useEffect(() => {
    if (!element.current) return;
    setWorkerUrl("/maplibre-gl-worker.mjs");
    const map = new MapLibreMap({
      container: element.current,
      style: offlineStyle(geographicStyle, latest.current.geometry),
      bounds: mapBounds(fitRef.current),
      fitBoundsOptions: { padding: FIT_PADDING },
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
    fitTargets.set(map, fitRef.current);
    fillCamera(map, fitRef.current);
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

  // A later data region (another case or mask) becomes the reset view; the camera stays where the reader left it.
  const [fw, fs, fe, fn] = fitBounds ?? bounds;
  useEffect(() => {
    fitRef.current = [fw, fs, fe, fn];
    if (mapRef.current) fitTargets.set(mapRef.current, fitRef.current);
  }, [fw, fs, fe, fn]);

  return { mapRef, status };
}
