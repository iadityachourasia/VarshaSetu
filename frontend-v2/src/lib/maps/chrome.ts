import type { Map as MapLibreMap } from "maplibre-gl";
import type { Feature, FeatureCollection, LineString, Point } from "geojson";
import { firstLabelLayer } from "./basemap";

type Bounds = [number, number, number, number];
type TickLabel = { text: string; axis: "lon" | "lat" };
/** Ticks closer than this to a corner of the domain are drawn but not labelled, so the corner labels never collide. */
const EDGE = 0.5;

/** Tick spacing in degrees for a map extent: fine enough to read a coordinate, sparse enough to stay quiet. */
export function graticuleStep(bounds: Bounds): number {
  const span = Math.max(bounds[2] - bounds[0], bounds[3] - bounds[1]);
  return span > 20 ? 5 : span > 8 ? 2 : 1;
}

export function graticule(bounds: Bounds): { lines: FeatureCollection<LineString>; labels: FeatureCollection<Point, TickLabel> } {
  const [west, south, east, north] = bounds;
  const step = graticuleStep(bounds);
  const lines: Feature<LineString>[] = [];
  const labels: Feature<Point, TickLabel>[] = [];
  for (let lon = Math.ceil(west / step) * step; lon <= east; lon += step) {
    lines.push({ type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: [[lon, south], [lon, north]] } });
    if (lon - west >= EDGE && east - lon >= EDGE) labels.push({ type: "Feature", properties: { text: `${lon}° E`, axis: "lon" }, geometry: { type: "Point", coordinates: [lon, south] } });
  }
  for (let lat = Math.ceil(south / step) * step; lat <= north; lat += step) {
    lines.push({ type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: [[west, lat], [east, lat]] } });
    if (lat - south >= EDGE && north - lat >= EDGE) labels.push({ type: "Feature", properties: { text: `${lat}° N`, axis: "lat" }, geometry: { type: "Point", coordinates: [west, lat] } });
  }
  return { lines: { type: "FeatureCollection", features: lines }, labels: { type: "FeatureCollection", features: labels } };
}

/**
 * Cartographic furniture shared by every map: a quiet coordinate graticule with degree labels on the edges of the data domain, and a dashed outline of that
 * domain so the edge of the data is never mistaken for the edge of the world. It carries no scientific value and never touches the science layers.
 */
export function installMapChrome(map: MapLibreMap, bounds: Bounds, dark: boolean): void {
  if (map.getSource("chrome-graticule")) return;
  const [west, south, east, north] = bounds;
  const { lines, labels } = graticule(bounds);
  const before = firstLabelLayer(map.getStyle());
  map.addSource("chrome-graticule", { type: "geojson", data: lines });
  map.addLayer({ id: "chrome-graticule-line", type: "line", source: "chrome-graticule", paint: { "line-color": dark ? "#ffffff" : "#1f3b47", "line-opacity": dark ? 0.14 : 0.16, "line-width": 0.6 } }, before);
  map.addSource("chrome-domain", { type: "geojson", data: { type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: [[west, south], [east, south], [east, north], [west, north], [west, south]] } } });
  map.addLayer({ id: "chrome-domain-outline", type: "line", source: "chrome-domain", paint: { "line-color": dark ? "#dcefed" : "#27474f", "line-opacity": 0.6, "line-width": 1.1, "line-dasharray": [3, 2] } }, before);
  if (!map.getStyle().glyphs) return;      // the offline style has no glyph endpoint; the lines alone still carry the grid
  map.addSource("chrome-graticule-labels", { type: "geojson", data: labels });
  map.addLayer({
    id: "chrome-graticule-label", type: "symbol", source: "chrome-graticule-labels",
    layout: { "text-field": ["get", "text"], "text-font": ["Noto Sans Regular"], "text-size": 10.5, "text-anchor": "bottom-left", "text-offset": [0.3, -0.25], "text-allow-overlap": false, "text-ignore-placement": true },
    paint: { "text-color": dark ? "#e6f1f0" : "#1b3640", "text-halo-color": dark ? "#071620" : "#f8faf8", "text-halo-width": 1.5, "text-opacity": 0.9 },
  });
}
