"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { type GeoJSONSource, type ImageSource, type Map } from "maplibre-gl";
import type { FeatureCollection, Polygon } from "geojson";
import type { Geometry, Grid } from "@/lib/api/science";
import { cellAt, rasterCoordinates, rasterPixels, validBounds, type CellSelection, type Palette } from "@/lib/maps/grid";
import { firstLabelLayer } from "@/lib/maps/basemap";
import { installDistrictLabels, updateDistrictLabels } from "@/lib/maps/label-layers";
import type { DistrictGeometry } from "@/lib/maps/district-labels";
import { emphasisFor } from "@/lib/maps/emphasis";
import { DURATION, easeOut, shouldAnimate } from "@/lib/motion";
import { MapAttribution } from "./map-attribution";
import { useMapEmphasis } from "./map-emphasis";
import { LocatorInset } from "./locator-inset";
import { mm, percent } from "@/lib/format";
import { useMapSettings } from "./map-settings";
import { useWeatherMap } from "./use-weather-map";

type Props = {
  id: string; title: string; subtitle: string;
  values: (number | null)[][]; mask: boolean[][]; grid: Grid; palette: Palette;
  unit?: string;
  /** How the hover reads a value: a classifier score (not a probability) or a yes/no forecast. Defaults to the palette's own reading. */
  valueFormat?: "score" | "decision";
  geometry?: Geometry["geometry"];
  selected: CellSelection | null; onSelect: (cell: CellSelection) => void;
  onReady?: (id: string, map: Map | null) => void;
  onMove?: (id: string, map: Map) => void;
  /** Maps drawn from the same grid can share one pointer: this reports the cell under it (or null on leaving) and `linkedHover` draws the cell another map reported. */
  onHoverCell?: (cell: CellSelection | null) => void;
  linkedHover?: CellSelection | null;
};

const sameCell = (a: CellSelection | null, b: CellSelection | null) => a === b || (a !== null && b !== null && a.row === b.row && a.column === b.column);

/**
 * Replace the displayed raster by fading the old picture out while the new one fades in. The previous picture is parked in a second image layer underneath;
 * both are repainted at the start (no transition) and then moved toward their end opacities, so the swap never flashes empty or shows a half-loaded state.
 */
function crossfadeRaster(map: Map, container: HTMLElement | null, previousImage: ImageData, nextImage: ImageData, opacity: number) {
  const next = map.getSource("science") as ImageSource | undefined, previous = map.getSource("science-prev") as ImageSource | undefined;
  if (!next || !previous || !map.getLayer("science-raster") || !map.getLayer("science-prev-raster")) { next?.updateImage({ image: nextImage }); return; }
  const set = (layer: string, duration: number, value: number) => {
    map.setPaintProperty(layer, "raster-opacity-transition", { duration, delay: 0 });
    map.setPaintProperty(layer, "raster-opacity", value);
  };
  previous.updateImage({ image: previousImage });
  next.updateImage({ image: nextImage });
  set("science-prev-raster", 0, opacity);
  set("science-raster", 0, 0);
  if (container) container.dataset.crossfades = String(Number(container.dataset.crossfades ?? "0") + 1);
  requestAnimationFrame(() => requestAnimationFrame(() => {
    if (!map.getLayer("science-raster")) return;
    set("science-prev-raster", DURATION.slow, 0);
    set("science-raster", DURATION.slow, opacity);
  }));
}

function selectedFeature(grid: Grid, cell: CellSelection | null): FeatureCollection<Polygon> {
  if (!cell) return { type: "FeatureCollection", features: [] };
  const half = grid.cell_size_degrees / 2;
  const latitude = grid.latitude_centers[cell.row], longitude = grid.longitude_centers[cell.column];
  const west = longitude - half, east = longitude + half, south = latitude - half, north = latitude + half;
  return { type: "FeatureCollection", features: [{ type: "Feature", properties: {}, geometry: { type: "Polygon", coordinates: [[[west, south], [east, south], [east, north], [west, north], [west, south]]] } }] };
}

export default function GridMap({ id, title, subtitle, values, mask, grid, palette, unit, valueFormat, geometry, selected, onSelect, onReady, onMove, onHoverCell, linkedHover = null }: Props) {
  const settings = useMapSettings();
  const container = useRef<HTMLDivElement>(null);
  const callbacks = useRef({ onSelect, onReady, onMove, onHoverCell });
  const [hover, setHover] = useState<CellSelection | null>(null);
  const [hoverDistrict, setHoverDistrict] = useState<string | null>(null);
  const dataBounds = useMemo(() => validBounds(grid, mask), [grid, mask]);
  const { emphasis } = useMapEmphasis();
  const activeEmphasis = emphasisFor(emphasis, palette);
  // `baseImage` is the picture of the data itself; `image` is the same picture with the legend emphasis (if any) applied. Only a change of the data crossfades.
  const basePixels = useMemo(() => rasterPixels(grid, values, mask, palette, settings.displayMode), [grid, values, mask, palette, settings.displayMode]);
  const pixels = useMemo(() => activeEmphasis ? rasterPixels(grid, values, mask, palette, settings.displayMode, activeEmphasis) : basePixels, [grid, values, mask, palette, settings.displayMode, activeEmphasis, basePixels]);
  const baseImage = useMemo(() => new ImageData(basePixels.data, basePixels.width, basePixels.height), [basePixels]);
  const image = useMemo(() => pixels === basePixels ? baseImage : new ImageData(pixels.data, pixels.width, pixels.height), [pixels, basePixels, baseImage]);
  const shown = useRef({ image, baseImage });
  const opacityRef = useRef(settings.opacity);
  const lastHover = useRef<CellSelection | null>(null);
  const pulseFrame = useRef(0);
  useEffect(() => { opacityRef.current = settings.opacity; }, [settings.opacity]);
  const geometryData = geometry as FeatureCollection | undefined;
  useEffect(() => { callbacks.current = { onSelect, onReady, onMove, onHoverCell }; }, [onSelect, onReady, onMove, onHoverCell]);

  const installLayers = useCallback((map: Map) => {
    const before = firstLabelLayer(map.getStyle());
    const resampling = settings.displayMode === "grid" ? "nearest" : "linear";
    map.addSource("science", { type: "image", coordinates: rasterCoordinates(grid) });
    (map.getSource("science") as ImageSource).updateImage({ image });
    map.addLayer({ id: "science-raster", type: "raster", source: "science", paint: {
      "raster-opacity": settings.opacity, "raster-opacity-transition": { duration: 0, delay: 0 },
      "raster-resampling": resampling,
      "raster-fade-duration": 0,
    } }, before);
    // The parked previous picture used by the crossfade; invisible until a change of data swaps pictures.
    map.addSource("science-prev", { type: "image", coordinates: rasterCoordinates(grid) });
    (map.getSource("science-prev") as ImageSource).updateImage({ image });
    map.addLayer({ id: "science-prev-raster", type: "raster", source: "science-prev", paint: {
      "raster-opacity": 0, "raster-opacity-transition": { duration: 0, delay: 0 }, "raster-resampling": resampling, "raster-fade-duration": 0,
    } }, "science-raster");
    map.addSource("district-overlay", { type: "geojson", data: geometryData ?? { type: "FeatureCollection", features: [] } });
    map.addLayer({ id: "district-overlay-hit", type: "fill", source: "district-overlay", paint: { "fill-color": "#ffffff", "fill-opacity": 0 } }, before);
    map.addLayer({ id: "district-overlay-line", type: "line", source: "district-overlay", layout: { visibility: settings.boundaries ? "visible" : "none" }, paint: { "line-color": settings.geographicStyle === "dark" ? "#c6dcda" : "#365664", "line-opacity": 0.39, "line-width": 0.65 } }, before);
    map.addSource("selected-grid-cell", { type: "geojson", data: selectedFeature(grid, selected) });
    map.addLayer({ id: "selected-grid-cell-outline", type: "line", source: "selected-grid-cell", paint: { "line-color": "#ffffff", "line-width": 2.5 } });
    map.addLayer({ id: "selected-grid-cell-pulse", type: "line", source: "selected-grid-cell", paint: { "line-color": "#ffffff", "line-width": 2.5, "line-opacity": 0, "line-blur": 1.5 } });
    map.addSource("linked-hover-cell", { type: "geojson", data: selectedFeature(grid, linkedHover) });
    map.addLayer({ id: "linked-hover-cell-outline", type: "line", source: "linked-hover-cell", paint: { "line-color": "#ffffff", "line-width": 1.4, "line-opacity": 0.9, "line-dasharray": [2, 2] } });
    installDistrictLabels(map, geometryData as DistrictGeometry | undefined, settings.geographicStyle);
    // Readiness means the exact scientific source and layers are installed;
    // remote basemap tiles may continue loading or fail independently.
    if (container.current) container.current.dataset.ready = "true";
  }, [grid, image, geometryData, selected, linkedHover, settings.opacity, settings.displayMode, settings.boundaries, settings.geographicStyle]);

  const { mapRef, status } = useWeatherMap({
    element: container, bounds: grid.bounds_west_south_east_north, fitBounds: dataBounds, geometry: geometryData,
    geographicStyle: settings.geographicStyle, onStyleReady: installLayers,
    onReady: (map) => callbacks.current.onReady?.(id, map),
  });

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    let userMove = false;
    const start = (event: { originalEvent?: Event }) => { userMove = Boolean(event.originalEvent); };
    const move = () => {
      if (container.current) container.current.dataset.camera = `${map.getCenter().lng.toFixed(5)},${map.getCenter().lat.toFixed(5)},${map.getZoom().toFixed(5)}`;
      if (userMove) callbacks.current.onMove?.(id, map);
    };
    const end = () => { userMove = false; };
    const hoverCell = (event: { lngLat: { lng: number; lat: number }; point: { x: number; y: number } }) => {
      const cell = cellAt(grid, event.lngLat.lng, event.lngLat.lat);
      setHover(cell);
      if (!sameCell(cell, lastHover.current)) { lastHover.current = cell; callbacks.current.onHoverCell?.(cell); }
      const district = map.getLayer("district-overlay-hit") ? map.queryRenderedFeatures([event.point.x, event.point.y], { layers: ["district-overlay-hit"] })[0] : null;
      setHoverDistrict(typeof district?.properties?.district_name === "string" ? district.properties.district_name : null);
    };
    const clickCell = (event: { lngLat: { lng: number; lat: number } }) => {
      const cell = cellAt(grid, event.lngLat.lng, event.lngLat.lat);
      if (cell) callbacks.current.onSelect(cell);
    };
    const leave = () => { lastHover.current = null; callbacks.current.onHoverCell?.(null); };
    const canvas = map.getCanvasContainer();
    map.on("movestart", start); map.on("move", move); map.on("moveend", end);
    map.on("mousemove", hoverCell); map.on("click", clickCell);
    canvas.addEventListener("mouseleave", leave);
    return () => { map.off("movestart", start); map.off("move", move); map.off("moveend", end); map.off("mousemove", hoverCell); map.off("click", clickCell); canvas.removeEventListener("mouseleave", leave); };
  }, [id, grid, mapRef]);

  useEffect(() => {
    const map = mapRef.current;
    const previous = shown.current;
    shown.current = { image, baseImage };
    if (previous.image === image) return;
    if (previous.baseImage !== baseImage && shouldAnimate() && map?.getLayer("science-prev-raster")) { crossfadeRaster(map, container.current, previous.image, image, opacityRef.current); return; }
    (map?.getSource("science") as ImageSource | undefined)?.updateImage({ image });
  }, [image, baseImage, mapRef]);
  useEffect(() => {
    const map = mapRef.current;
    if (!map?.getLayer("science-raster")) return;
    const resampling = settings.displayMode === "grid" ? "nearest" : "linear";
    map.setPaintProperty("science-raster", "raster-opacity-transition", { duration: 0, delay: 0 });
    map.setPaintProperty("science-raster", "raster-opacity", settings.opacity);
    map.setPaintProperty("science-raster", "raster-resampling", resampling);
    if (map.getLayer("science-prev-raster")) map.setPaintProperty("science-prev-raster", "raster-resampling", resampling);
  }, [mapRef, settings.opacity, settings.displayMode]);
  useEffect(() => {
    const map = mapRef.current;
    if (map?.getLayer("district-overlay-line")) map.setLayoutProperty("district-overlay-line", "visibility", settings.boundaries ? "visible" : "none");
  }, [mapRef, settings.boundaries]);
  useEffect(() => { (mapRef.current?.getSource("district-overlay") as GeoJSONSource | undefined)?.setData(geometryData ?? { type: "FeatureCollection", features: [] }); }, [geometryData, mapRef]);
  useEffect(() => { const map = mapRef.current; if (map) updateDistrictLabels(map, geometryData as DistrictGeometry | undefined, settings.geographicStyle); }, [geometryData, mapRef, settings.geographicStyle]);
  useEffect(() => { (mapRef.current?.getSource("selected-grid-cell") as GeoJSONSource | undefined)?.setData(selectedFeature(grid, selected)); }, [selected, grid, mapRef]);
  useEffect(() => { (mapRef.current?.getSource("linked-hover-cell") as GeoJSONSource | undefined)?.setData(selectedFeature(grid, linkedHover)); }, [linkedHover, grid, mapRef]);
  // State of the interactions, readable by tests and tooling without inspecting pixels.
  useEffect(() => {
    const node = container.current;
    if (!node) return;
    node.dataset.emphasis = activeEmphasis ? `${activeEmphasis.lo}:${activeEmphasis.hi}` : "";
    node.dataset.linkedHover = linkedHover ? `${linkedHover.row},${linkedHover.column}` : "";
  }, [activeEmphasis, linkedHover]);
  // A ring leaves the cell that has just been selected, so the eye finds it; it never runs for the first selection of a page load or for reduced motion.
  const previousSelected = useRef(selected);
  useEffect(() => {
    const map = mapRef.current;
    const changed = !sameCell(previousSelected.current, selected);
    previousSelected.current = selected;
    if (!changed || !selected || !shouldAnimate() || !map?.getLayer("selected-grid-cell-pulse")) return;
    cancelAnimationFrame(pulseFrame.current);
    if (container.current) container.current.dataset.pulses = String(Number(container.current.dataset.pulses ?? "0") + 1);
    let start: number | null = null;
    const tick = (now: number) => {
      if (!map.getLayer("selected-grid-cell-pulse")) return;
      start ??= now;
      const progress = Math.min(1, (now - start) / 650);
      map.setPaintProperty("selected-grid-cell-pulse", "line-width", 2.5 + 9 * easeOut(progress));
      map.setPaintProperty("selected-grid-cell-pulse", "line-opacity", 0.85 * (1 - progress));
      if (progress < 1) pulseFrame.current = requestAnimationFrame(tick);
    };
    pulseFrame.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(pulseFrame.current);
  }, [selected, mapRef]);

  const hoveredValue = hover ? values[hover.row]?.[hover.column] : null;
  const hoveredValid = hover ? mask[hover.row]?.[hover.column] : false;
  return <section className="map-panel" aria-label={`${title} map`}>
    <div className="map-panel-heading"><div><strong>{title}</strong><span>{subtitle}</span></div><span className={`model-dot model-${id}`} aria-hidden="true" /></div>
    <div className="map-surface">
      <div ref={container} className="map-canvas" role="img" aria-label={`${title} 49 by 49 historical ${palette === "rainfall" ? "rainfall" : palette === "probability" ? "probability" : "forecast-field"} grid. Display interpolation does not change original values; use the coordinate inspector for keyboard access.`} />
      <LocatorInset bounds={grid.bounds_west_south_east_north} theme={settings.geographicStyle} />
      <MapAttribution status={status} />
      {status === "offline" ? <span className="map-offline-badge">Offline geography</span> : null}
      {status === "loading" ? <span className="map-offline-badge">Loading geography…</span> : null}
      {hover ? <div className="map-hover" role="status">{hoverDistrict ? <span className="map-hover-district">{hoverDistrict} · </span> : null}{grid.latitude_centers[hover.row].toFixed(2)}° N · {grid.longitude_centers[hover.column].toFixed(2)}° E <strong>{hoveredValid && hoveredValue != null ? valueFormat === "decision" ? (hoveredValue >= 0.5 ? "Forecast: yes" : "Forecast: no") : valueFormat === "score" ? `score ${hoveredValue.toFixed(3)}` : palette === "rainfall" ? mm(hoveredValue) : palette === "probability" ? percent(hoveredValue) : `${hoveredValue.toFixed(palette === "q700" ? 4 : 2)} ${unit ?? ""}` : "Unavailable — masked reference cell"}</strong></div> : null}
    </div>
  </section>;
}
