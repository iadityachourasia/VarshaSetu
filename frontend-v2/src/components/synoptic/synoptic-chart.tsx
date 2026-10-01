"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQueries, useQuery } from "@tanstack/react-query";
import { Marker, type GeoJSONSource, type Map as MapLibreMap } from "maplibre-gl";
import type { Feature, FeatureCollection, LineString, Polygon } from "geojson";
import { OperationalApiError, getOperationalAtmosphere, type OperationalAtmosphericField, type OperationalYear } from "@/lib/api/operational";
import { geometrySchema, getScience } from "@/lib/api/science";
import { firstLabelLayer } from "@/lib/maps/basemap";
import {
  cellPolygons, contourFeatures, contourLevels, lineLength, lineMidpoint, niceInterval, valueRange, windArrows, type Matrix,
} from "@/lib/synoptic/geometry";
import { MapAttribution } from "@/components/maps/map-attribution";
import { MapControls } from "@/components/maps/map-controls";
import { useMapSettings } from "@/components/maps/map-settings";
import { useWeatherMap } from "@/components/maps/use-weather-map";
import { ErrorState, LoadingState } from "@/components/science/common";

const FIELDS = ["u850", "v850", "q700", "z500", "mslp", "pwat"] as const;
type FieldName = (typeof FIELDS)[number];
type Shading = "pwat" | "q700" | "none";
const SHADING_LABEL: Record<Shading, string> = { pwat: "Precipitable water (kg/m²)", q700: "700-hPa specific humidity (g/kg)", none: "No shading" };
const BOUNDS: [number, number, number, number] = [55, 5, 95, 30];
const RAINFALL_DOMAIN: [number, number, number, number] = [68, 10, 80, 22];
const STRIDE = 2; // one arrow per degree on the 0.5-degree grid
const ARROW_DEGREES_PER_MS = 0.06;
const RAMP = ["#0b2a4a", "#1d6f8f", "#27a18a", "#8fd16b", "#f4e04d"];

const empty = { type: "FeatureCollection", features: [] } as FeatureCollection;
const toMatrix = (values: unknown[]): Matrix => (values as (number | null)[][]);
const scale = (field: FieldName, matrix: Matrix): Matrix => matrix.map((row) => row.map((v) => (v == null ? null : field === "mslp" ? v / 100 : field === "q700" ? v * 1000 : v)));

function shadeFeatures(values: Matrix, lat: number[], lon: number[], spacing: number): FeatureCollection<Polygon> {
  return { type: "FeatureCollection", features: cellPolygons(values, lat, lon, spacing).map((cell) => ({ type: "Feature", properties: { v: cell.value }, geometry: { type: "Polygon", coordinates: [cell.ring] } })) };
}

function lineFeatures(features: { level: number; lines: [number, number][][] }[]): FeatureCollection<LineString> {
  return {
    type: "FeatureCollection",
    features: features.flatMap(({ level, lines }) => lines.map((line): Feature<LineString> => ({ type: "Feature", properties: { level }, geometry: { type: "LineString", coordinates: line } }))),
  };
}

function rampExpression(min: number, max: number): unknown[] {
  const stops = RAMP.flatMap((color, index) => [min + ((max - min) * index) / (RAMP.length - 1), color]);
  return ["interpolate", ["linear"], ["get", "v"], ...stops];
}

function boxFeature([west, south, east, north]: [number, number, number, number]): FeatureCollection<LineString> {
  return { type: "FeatureCollection", features: [{ type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: [[west, south], [east, south], [east, north], [west, north], [west, south]] } }] };
}

type Product = {
  lat: number[]; lon: number[]; spacing: number;
  shade: Record<Exclude<Shading, "none">, { collection: FeatureCollection<Polygon>; min: number; max: number }>;
  height: { collection: FeatureCollection<LineString>; labels: { level: number; at: [number, number] }[]; interval: number; count: number };
  pressure: { collection: FeatureCollection<LineString>; labels: { level: number; at: [number, number] }[]; interval: number; count: number };
  wind: { collection: FeatureCollection<LineString>; count: number; maxSpeed: number };
};

function contourProduct(values: Matrix, lat: number[], lon: number[], target: number) {
  const range = valueRange(values);
  if (!range) return { collection: lineFeatures([]), labels: [], interval: 0, count: 0 };
  const interval = niceInterval(range.min, range.max, target);
  const features = contourFeatures(values, lat, lon, contourLevels(range.min, range.max, interval));
  const labels = features.map(({ level, lines }) => {
    const longest = lines.reduce((a, b) => (lineLength(b) > lineLength(a) ? b : a));
    return { level, at: lineMidpoint(longest), length: lineLength(longest) };
  }).filter((label) => label.length > 3).map(({ level, at }) => ({ level, at }));
  return { collection: lineFeatures(features), labels, interval, count: features.length };
}

function buildProduct(fields: Record<FieldName, OperationalAtmosphericField>): Product {
  const reference = fields.pwat;
  const lat = reference.latitude_centers, lon = reference.longitude_centers, spacing = reference.grid_spacing_degrees;
  const matrices = Object.fromEntries(FIELDS.map((name) => [name, scale(name, toMatrix(fields[name].values))])) as Record<FieldName, Matrix>;
  const shade = (name: "pwat" | "q700") => {
    const range = valueRange(matrices[name]) ?? { min: 0, max: 1 };
    return { collection: shadeFeatures(matrices[name], lat, lon, spacing), min: range.min, max: range.max };
  };
  const arrows = windArrows(matrices.u850, matrices.v850, lat, lon, { stride: STRIDE, degreesPerMetreSecond: ARROW_DEGREES_PER_MS });
  return {
    lat, lon, spacing,
    shade: { pwat: shade("pwat"), q700: shade("q700") },
    height: contourProduct(matrices.z500, lat, lon, 10),
    pressure: contourProduct(matrices.mslp, lat, lon, 12),
    wind: {
      collection: { type: "FeatureCollection", features: arrows.map((arrow) => ({ type: "Feature", properties: { speed: arrow.speed }, geometry: { type: "LineString", coordinates: arrow.line } })) },
      count: arrows.length, maxSpeed: arrows.reduce((m, a) => Math.max(m, a.speed), 0),
    },
  };
}

function nearestIndex(axis: number[], value: number) {
  return axis.reduce((best, v, i) => (Math.abs(v - value) < Math.abs(axis[best] - value) ? i : best), 0);
}

export function SynopticChart({ year, caseId }: { year: OperationalYear; caseId: string }) {
  const settings = useMapSettings();
  const container = useRef<HTMLDivElement>(null);
  const frame = useRef<HTMLDivElement>(null);
  const markers = useRef<Marker[]>([]);
  const [shading, setShading] = useState<Shading>("pwat");
  const [show, setShow] = useState({ wind: true, height: true, pressure: true, domain: true });
  const [point, setPoint] = useState({ lat: 15, lon: 75 });

  const results = useQueries({ queries: FIELDS.map((name) => ({ queryKey: ["synoptic-field", year, caseId, name], queryFn: () => getOperationalAtmosphere(year, caseId, name), staleTime: 5 * 60_000, retry: 1 })) });
  const queries = FIELDS.map((name, index) => ({ name, query: results[index] }));
  const geometry = useQuery({ queryKey: ["district-geometry"], queryFn: () => getScience("/geometry/districts", geometrySchema) });
  const failed = queries.find(({ query }) => query.isError)?.query.error;
  const ready = queries.every(({ query }) => query.data);
  // Rebuild the (comparatively expensive) geometry only when the fetched data actually change.
  const dataSignature = results.map((result) => result.dataUpdatedAt).join(",");
  const product = useMemo(() => {
    if (!ready) return null;
    return buildProduct(Object.fromEntries(queries.map(({ name, query }) => [name, query.data])) as Record<FieldName, OperationalAtmosphericField>);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, dataSignature]);
  const latest = useRef({ product, shading, show, settings });
  useEffect(() => { latest.current = { product, shading, show, settings }; }, [product, shading, show, settings]);

  const apply = useCallback((map: MapLibreMap) => {
    const { product: current, shading: shade, show: visible } = latest.current;
    if (!current) return;
    const set = (id: string, data: FeatureCollection) => (map.getSource(id) as GeoJSONSource | undefined)?.setData(data);
    const shaded = shade === "none" ? null : current.shade[shade];
    set("syn-shade", shaded ? shaded.collection : empty);
    set("syn-height", current.height.collection);
    set("syn-pressure", current.pressure.collection);
    set("syn-wind", current.wind.collection);
    if (map.getLayer("syn-shade-fill") && shaded) map.setPaintProperty("syn-shade-fill", "fill-color", rampExpression(shaded.min, shaded.max) as never);
    const vis = (id: string, on: boolean) => map.getLayer(id) && map.setLayoutProperty(id, "visibility", on ? "visible" : "none");
    vis("syn-height-line", visible.height); vis("syn-pressure-line", visible.pressure); vis("syn-wind-line", visible.wind); vis("syn-domain-line", visible.domain);
    markers.current.forEach((marker) => marker.remove());
    markers.current = [];
    const label = (text: string, at: [number, number], className: string) => {
      const element = document.createElement("span");
      element.className = `synoptic-label ${className}`;
      element.textContent = text;
      markers.current.push(new Marker({ element }).setLngLat(at).addTo(map));
    };
    if (visible.height) current.height.labels.forEach((l) => label(String(Math.round(l.level)), l.at, "synoptic-label-height"));
    if (visible.pressure) current.pressure.labels.forEach((l) => label(String(Math.round(l.level)), l.at, "synoptic-label-pressure"));
    const element = container.current;
    if (element) {
      element.dataset.shadedCells = String(shaded?.collection.features.length ?? 0);
      element.dataset.heightContours = String(visible.height ? current.height.count : 0);
      element.dataset.pressureContours = String(visible.pressure ? current.pressure.count : 0);
      element.dataset.windArrows = String(visible.wind ? current.wind.count : 0);
    }
  }, []);

  const installLayers = useCallback((map: MapLibreMap) => {
    const before = firstLabelLayer(map.getStyle());
    const dark = latest.current.settings.geographicStyle === "dark";
    for (const id of ["syn-shade", "syn-height", "syn-pressure", "syn-wind"]) map.addSource(id, { type: "geojson", data: empty });
    map.addSource("syn-domain", { type: "geojson", data: boxFeature(RAINFALL_DOMAIN) });
    map.addLayer({ id: "syn-shade-fill", type: "fill", source: "syn-shade", paint: { "fill-color": "#27a18a", "fill-opacity": 0.62, "fill-antialias": false } }, before);
    map.addLayer({ id: "syn-height-line", type: "line", source: "syn-height", layout: { "line-join": "round" }, paint: { "line-color": dark ? "#f2c36b" : "#8a4b08", "line-width": 1.3 } }, before);
    map.addLayer({ id: "syn-pressure-line", type: "line", source: "syn-pressure", layout: { "line-join": "round" }, paint: { "line-color": dark ? "#9ad0ff" : "#14406b", "line-width": 1.1, "line-dasharray": [3, 2] } }, before);
    map.addLayer({ id: "syn-wind-line", type: "line", source: "syn-wind", layout: { "line-cap": "round", "line-join": "round" }, paint: { "line-color": dark ? "#ffffff" : "#10222c", "line-width": 1.15, "line-opacity": 0.92 } }, before);
    map.addLayer({ id: "syn-domain-line", type: "line", source: "syn-domain", paint: { "line-color": "#ff5d73", "line-width": 1.6, "line-dasharray": [2, 2] } });
    apply(map);
    if (container.current) container.current.dataset.ready = "true";
  }, [apply]);

  const { mapRef, status } = useWeatherMap({
    element: container, bounds: BOUNDS, geometry: geometry.data?.geometry as FeatureCollection | undefined,
    geographicStyle: settings.geographicStyle, onStyleReady: installLayers,
  });
  // Redraw whenever the data or the layer choices change. Guard on our own source, not on isStyleLoaded(): that stays false while
  // basemap tiles are still loading, which would silently swallow a toggle.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    try { if (map.getSource("syn-shade")) apply(map); } catch { /* style is being replaced; installLayers applies the latest state when it is ready */ }
  }, [product, shading, show, mapRef, apply]);
  useEffect(() => () => { markers.current.forEach((marker) => marker.remove()); markers.current = []; }, []);
  // The frame is hidden until the data arrive, so the map was created in a zero-size container; refit once it has its real size.
  const fitted = useRef(false);
  useEffect(() => {
    const map = mapRef.current;
    if (!product || !map || fitted.current) return;
    fitted.current = true;
    requestAnimationFrame(() => { map.resize(); map.fitBounds([[BOUNDS[0], BOUNDS[1]], [BOUNDS[2], BOUNDS[3]]], { padding: 14, duration: 0 }); });
  }, [product, mapRef]);

  // The map hook initialises once, on first mount, so the container must exist in every state (loading, failed, ready).
  const integrity = failed instanceof OperationalApiError && failed.kind === "INTEGRITY_FAILURE";
  const ineligible = failed instanceof OperationalApiError && failed.status === 404;
  const failureMessage = failed ? (integrity ? `Scientific artifact integrity check failed: ${(failed as Error).message}. This is a hard failure.` : ineligible
    ? "The atmospheric fields of this case did not pass canonical quality control, so no synoptic chart is shown for it." : "The atmospheric fields for this case could not be loaded.") : null;

  const reference = queries[0].query.data ?? null;
  const shaded = !product || shading === "none" ? null : product.shade[shading];
  const row = product ? nearestIndex(product.lat, point.lat) : 0, column = product ? nearestIndex(product.lon, point.lon) : 0;
  const at = (name: FieldName) => (queries.find((q) => q.name === name)!.query.data?.values[row]?.[column] ?? null) as number | null;
  const speed = Math.hypot(at("u850") ?? NaN, at("v850") ?? NaN);
  const f = (value: number | null | undefined, digits: number) => (value == null || !Number.isFinite(value) ? "unavailable" : value.toFixed(digits));

  return <section className="synoptic" aria-label="Synoptic chart">
    {failureMessage ? <ErrorState message={failureMessage} /> : null}
    {!product && !failed ? <LoadingState label="Loading wide-domain atmosphere" /> : null}
    {product ? <div className="phase5-controls" role="group" aria-label="Synoptic layers">
      <label>Shading<select value={shading} onChange={(event) => setShading(event.target.value as Shading)}>{(Object.keys(SHADING_LABEL) as Shading[]).map((key) => <option key={key} value={key}>{SHADING_LABEL[key]}</option>)}</select></label>
      <label className="synoptic-check"><input type="checkbox" checked={show.wind} onChange={(e) => setShow({ ...show, wind: e.target.checked })} /> 850-hPa wind</label>
      <label className="synoptic-check"><input type="checkbox" checked={show.height} onChange={(e) => setShow({ ...show, height: e.target.checked })} /> 500-hPa height</label>
      <label className="synoptic-check"><input type="checkbox" checked={show.pressure} onChange={(e) => setShow({ ...show, pressure: e.target.checked })} /> Sea-level pressure</label>
      <label className="synoptic-check"><input type="checkbox" checked={show.domain} onChange={(e) => setShow({ ...show, domain: e.target.checked })} /> Rainfall domain</label>
    </div> : null}
    <MapControls onReset={() => mapRef.current?.fitBounds([[BOUNDS[0], BOUNDS[1]], [BOUNDS[2], BOUNDS[3]]], { padding: 14, duration: 0 })} onZoom={(delta) => mapRef.current?.zoomTo((mapRef.current?.getZoom() ?? 3) + delta, { duration: 150 })}
      onFullscreen={async () => { if (document.fullscreenElement) await document.exitFullscreen(); else await frame.current?.requestFullscreen(); mapRef.current?.resize(); }} />
    <div ref={frame} className="map-panel synoptic-frame" hidden={!product}>
      <div className="map-panel-heading"><div><strong>Synoptic chart{reference ? ` · forecast hour ${reference.forecast_hour}` : ""}</strong><span>Frozen forecast fields on the 0.5° context grid · 5–30° N, 55–95° E</span></div></div>
      <div className="map-surface synoptic-surface">
        <div ref={container} className="map-canvas synoptic-canvas" role="img"
          aria-label="Synoptic chart of the wide forecast domain: 850-hPa wind arrows, 500-hPa geopotential height contours, sea-level pressure isobars and shaded moisture. Use the point reader below for exact values." />
        <MapAttribution status={status} />
        {status === "offline" ? <span className="map-offline-badge">Offline geography</span> : null}
      </div>
    </div>
    {product ? <><div className="synoptic-legend" aria-label="Chart key">
      {shaded ? <div className="synoptic-ramp"><span>{shaded.min.toFixed(shading === "q700" ? 1 : 0)}</span><i style={{ background: `linear-gradient(90deg, ${RAMP.join(", ")})` }} aria-hidden="true" /><span>{shaded.max.toFixed(shading === "q700" ? 1 : 0)}</span><small>{SHADING_LABEL[shading]}</small></div> : null}
      <p><b>500-hPa height</b> solid lines every {product.height.interval} gpm · <b>Sea-level pressure</b> dashed lines every {product.pressure.interval} hPa · <b>Wind</b> one arrow per 1°, arrow length 0.6° = 10 m/s (maximum {product.wind.maxSpeed.toFixed(1)} m/s) · dashed red box = the 49 × 49 rainfall verification domain</p>
    </div>
    <div className="phase5-inspector synoptic-reader">
      <div><span className="small-label">POINT READER</span><h2>{product.lat[row].toFixed(1)}° N · {product.lon[column].toFixed(1)}° E</h2><p>Nearest cell of the 51 × 81 context grid</p></div>
      <div className="phase5-point-values">
        <span>Wind <strong>{f(speed, 1)} m/s</strong></span><span>U / V <strong>{f(at("u850"), 1)} / {f(at("v850"), 1)}</strong></span>
        <span>Height 500 hPa <strong>{f(at("z500"), 0)} gpm</strong></span><span>Sea-level pressure <strong>{f(at("mslp") == null ? null : (at("mslp") as number) / 100, 1)} hPa</strong></span>
        <span>Precipitable water <strong>{f(at("pwat"), 1)} kg/m²</strong></span><span>Humidity 700 hPa <strong>{f(at("q700") == null ? null : (at("q700") as number) * 1000, 2)} g/kg</strong></span>
      </div>
      <div className="cell-controls">
        <label>Latitude<select value={product.lat[row]} onChange={(e) => setPoint({ ...point, lat: Number(e.target.value) })}>{product.lat.map((v) => <option key={v} value={v}>{v.toFixed(1)}° N</option>)}</select></label>
        <label>Longitude<select value={product.lon[column]} onChange={(e) => setPoint({ ...point, lon: Number(e.target.value) })}>{product.lon.map((v) => <option key={v} value={v}>{v.toFixed(1)}° E</option>)}</select></label>
      </div>
    </div>
    <p className="map-method-note">{reference?.coordinate_note}</p></> : null}
  </section>;
}
