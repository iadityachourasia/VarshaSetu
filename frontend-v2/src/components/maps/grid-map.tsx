"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { type GeoJSONSource, type ImageSource, type Map } from "maplibre-gl";
import type { FeatureCollection, Polygon } from "geojson";
import type { Geometry, Grid } from "@/lib/api/science";
import { cellAt, rasterCoordinates, rasterPixels, type CellSelection, type Palette } from "@/lib/maps/grid";
import { firstLabelLayer } from "@/lib/maps/basemap";
import { installDistrictLabels, updateDistrictLabels } from "@/lib/maps/label-layers";
import type { DistrictGeometry } from "@/lib/maps/district-labels";
import { MapAttribution } from "./map-attribution";
import { LocatorInset } from "./locator-inset";
import { mm, percent } from "@/lib/format";
import { useMapSettings } from "./map-settings";
import { useWeatherMap } from "./use-weather-map";

type Props = {
  id: string; title: string; subtitle: string;
  values: (number | null)[][]; mask: boolean[][]; grid: Grid; palette: Palette;
  unit?: string;
  geometry?: Geometry["geometry"];
  selected: CellSelection | null; onSelect: (cell: CellSelection) => void;
  onReady?: (id: string, map: Map | null) => void;
  onMove?: (id: string, map: Map) => void;
};

function selectedFeature(grid: Grid, cell: CellSelection | null): FeatureCollection<Polygon> {
  if (!cell) return { type: "FeatureCollection", features: [] };
  const half = grid.cell_size_degrees / 2;
  const latitude = grid.latitude_centers[cell.row], longitude = grid.longitude_centers[cell.column];
  const west = longitude - half, east = longitude + half, south = latitude - half, north = latitude + half;
  return { type: "FeatureCollection", features: [{ type: "Feature", properties: {}, geometry: { type: "Polygon", coordinates: [[[west, south], [east, south], [east, north], [west, north], [west, south]]] } }] };
}

export default function GridMap({ id, title, subtitle, values, mask, grid, palette, unit, geometry, selected, onSelect, onReady, onMove }: Props) {
  const settings = useMapSettings();
  const container = useRef<HTMLDivElement>(null);
  const callbacks = useRef({ onSelect, onReady, onMove });
  const [hover, setHover] = useState<CellSelection | null>(null);
  const [hoverDistrict, setHoverDistrict] = useState<string | null>(null);
  const pixels = useMemo(() => rasterPixels(grid, values, mask, palette, settings.displayMode), [grid, values, mask, palette, settings.displayMode]);
  const image = useMemo(() => new ImageData(pixels.data, pixels.width, pixels.height), [pixels]);
  const geometryData = geometry as FeatureCollection | undefined;
  useEffect(() => { callbacks.current = { onSelect, onReady, onMove }; }, [onSelect, onReady, onMove]);

  const installLayers = useCallback((map: Map) => {
    const before = firstLabelLayer(map.getStyle());
    map.addSource("science", { type: "image", coordinates: rasterCoordinates(grid) });
    (map.getSource("science") as ImageSource).updateImage({ image });
    map.addLayer({ id: "science-raster", type: "raster", source: "science", paint: {
      "raster-opacity": settings.opacity,
      "raster-resampling": settings.displayMode === "grid" ? "nearest" : "linear",
      "raster-fade-duration": 0,
    } }, before);
    map.addSource("district-overlay", { type: "geojson", data: geometryData ?? { type: "FeatureCollection", features: [] } });
    map.addLayer({ id: "district-overlay-hit", type: "fill", source: "district-overlay", paint: { "fill-color": "#ffffff", "fill-opacity": 0 } }, before);
    map.addLayer({ id: "district-overlay-line", type: "line", source: "district-overlay", layout: { visibility: settings.boundaries ? "visible" : "none" }, paint: { "line-color": settings.geographicStyle === "dark" ? "#c6dcda" : "#365664", "line-opacity": 0.39, "line-width": 0.65 } }, before);
    map.addSource("selected-grid-cell", { type: "geojson", data: selectedFeature(grid, selected) });
    map.addLayer({ id: "selected-grid-cell-outline", type: "line", source: "selected-grid-cell", paint: { "line-color": "#ffffff", "line-width": 2.5 } });
    installDistrictLabels(map, geometryData as DistrictGeometry | undefined, settings.geographicStyle);
    // Readiness means the exact scientific source and layers are installed;
    // remote basemap tiles may continue loading or fail independently.
    if (container.current) container.current.dataset.ready = "true";
  }, [grid, image, geometryData, selected, settings.opacity, settings.displayMode, settings.boundaries, settings.geographicStyle]);

  const { mapRef, status } = useWeatherMap({
    element: container, bounds: grid.bounds_west_south_east_north, geometry: geometryData,
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
      setHover(cellAt(grid, event.lngLat.lng, event.lngLat.lat));
      const district = map.getLayer("district-overlay-hit") ? map.queryRenderedFeatures([event.point.x, event.point.y], { layers: ["district-overlay-hit"] })[0] : null;
      setHoverDistrict(typeof district?.properties?.district_name === "string" ? district.properties.district_name : null);
    };
    const clickCell = (event: { lngLat: { lng: number; lat: number } }) => {
      const cell = cellAt(grid, event.lngLat.lng, event.lngLat.lat);
      if (cell) callbacks.current.onSelect(cell);
    };
    map.on("movestart", start); map.on("move", move); map.on("moveend", end);
    map.on("mousemove", hoverCell); map.on("click", clickCell);
    return () => { map.off("movestart", start); map.off("move", move); map.off("moveend", end); map.off("mousemove", hoverCell); map.off("click", clickCell); };
  }, [id, grid, mapRef]);

  useEffect(() => { (mapRef.current?.getSource("science") as ImageSource | undefined)?.updateImage({ image }); }, [image, mapRef]);
  useEffect(() => {
    const map = mapRef.current;
    if (!map?.getLayer("science-raster")) return;
    map.setPaintProperty("science-raster", "raster-opacity", settings.opacity);
    map.setPaintProperty("science-raster", "raster-resampling", settings.displayMode === "grid" ? "nearest" : "linear");
  }, [mapRef, settings.opacity, settings.displayMode]);
  useEffect(() => {
    const map = mapRef.current;
    if (map?.getLayer("district-overlay-line")) map.setLayoutProperty("district-overlay-line", "visibility", settings.boundaries ? "visible" : "none");
  }, [mapRef, settings.boundaries]);
  useEffect(() => { (mapRef.current?.getSource("district-overlay") as GeoJSONSource | undefined)?.setData(geometryData ?? { type: "FeatureCollection", features: [] }); }, [geometryData, mapRef]);
  useEffect(() => { const map = mapRef.current; if (map) updateDistrictLabels(map, geometryData as DistrictGeometry | undefined, settings.geographicStyle); }, [geometryData, mapRef, settings.geographicStyle]);
  useEffect(() => { (mapRef.current?.getSource("selected-grid-cell") as GeoJSONSource | undefined)?.setData(selectedFeature(grid, selected)); }, [selected, grid, mapRef]);

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
      {hover ? <div className="map-hover" role="status">{hoverDistrict ? <span className="map-hover-district">{hoverDistrict} · </span> : null}{grid.latitude_centers[hover.row].toFixed(2)}° N · {grid.longitude_centers[hover.column].toFixed(2)}° E <strong>{hoveredValid && hoveredValue != null ? palette === "rainfall" ? mm(hoveredValue) : palette === "probability" ? percent(hoveredValue) : `${hoveredValue.toFixed(palette === "q700" ? 4 : 2)} ${unit ?? ""}` : "Unavailable — masked reference cell"}</strong></div> : null}
    </div>
  </section>;
}
