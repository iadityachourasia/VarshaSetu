import type { GeoJSONSource, Map as MapLibreMap, StyleSpecification } from "maplibre-gl";
import type { FeatureCollection, Point } from "geojson";
import { districtLabelPoints, oneDistrictLabel, type DistrictGeometry, type DistrictLabel } from "./district-labels";
import type { GeographicStyle } from "./basemap";

type LabelCollection = FeatureCollection<Point, DistrictLabel["properties"]>;
const EMPTY: LabelCollection = { type: "FeatureCollection", features: [] };
const DISTRICT_LABEL_LAYERS = ["district-label-tier-0", "district-label-tier-1", "district-label-tier-2", "district-selected-label"];

function reportRenderedLabels(map: MapLibreMap): void {
  map.getContainer().dataset.districtLabelsRendered = "0";
  map.once("idle", () => {
    if (!map.getLayer("district-label-tier-0")) return;
    map.getContainer().dataset.districtLabelsRendered = String(map.queryRenderedFeatures({ layers: DISTRICT_LABEL_LAYERS }).length);
  });
}

// OpenFreeMap currently serves Noto Sans Regular/Bold from its glyph endpoint.
// These icon sprites are generated only for the local offline style, which has
// no glyph endpoint and must continue to label districts without network.
function offlineLabelImage(name: string, selected: boolean, dark: boolean): ImageData {
  const canvas = document.createElement("canvas");
  const context = canvas.getContext("2d");
  if (!context) throw new Error("Canvas is unavailable for offline map labels");
  const font = `${selected ? "700 14" : "600 12"}px Arial, sans-serif`;
  context.font = font;
  const width = Math.ceil(context.measureText(name).width + 14);
  canvas.width = Math.max(18, width * 2);
  canvas.height = (selected ? 25 : 22) * 2;
  context.scale(2, 2);
  context.font = font;
  context.textBaseline = "middle";
  context.lineJoin = "round";
  context.lineWidth = selected ? 4 : 3.5;
  context.strokeStyle = dark ? "#071620" : "#f7faf7";
  context.fillStyle = dark ? "#f4faf8" : "#172f39";
  context.strokeText(name, 7, canvas.height / 4);
  context.fillText(name, 7, canvas.height / 4);
  return context.getImageData(0, 0, canvas.width, canvas.height);
}

export function readableGeographyStyle(style: StyleSpecification, theme: GeographicStyle): StyleSpecification {
  const dark = theme === "dark";
  const important = dark ? ["place_city", "place_city_large", "place_state"] : ["label_city", "label_city_capital", "label_state"];
  for (const layer of style.layers) {
    if (important.includes(layer.id) && layer.type === "symbol") {
      layer.paint = {
        ...layer.paint,
        "text-color": dark ? (layer.id === "place_state" ? "#c8dce2" : "#f3f9f8") : "#19343f",
        "text-halo-color": dark ? "#091923" : "#f8faf8",
        "text-halo-width": dark ? 1.8 : 1.5,
        "text-halo-blur": 0.3,
      };
    }
    if (dark && layer.type === "symbol" && ["place_other", "place_suburb", "place_village", "place_town"].includes(layer.id)) {
      layer.minzoom = Math.max(layer.minzoom ?? 0, 6);
    }
    if (dark && layer.type === "symbol" && ["highway_name_other", "highway_name_motorway"].includes(layer.id)) {
      layer.paint = { ...layer.paint, "text-opacity": 0.35 };
    }
    if (dark && layer.type === "line" && layer.id === "boundary_state") {
      layer.paint = { ...layer.paint, "line-color": "#78929c", "line-opacity": 0.52, "line-width": 0.8 };
    }
    if (dark && layer.type === "line" && /^(highway_|tunnel_|bridge_|railway)/.test(layer.id)) {
      layer.paint = { ...layer.paint, "line-opacity": 0.2 };
    }
  }
  return style;
}

export function installDistrictLabels(map: MapLibreMap, geometry: DistrictGeometry | undefined, theme: GeographicStyle, selectedId: string | null = null): void {
  const labels = geometry ? districtLabelPoints(geometry) : EMPTY;
  const offline = !map.getStyle().glyphs;
  const dark = theme === "dark";
  const compact = map.getContainer().clientWidth < 520;       // the three-panel layouts: fewer, smaller names so they do not bury the field
  map.getContainer().dataset.districtLabelCount = String(labels.features.length);
  map.getContainer().dataset.districtLabelMode = offline ? "offline-icons" : "online-text";
  map.addSource("district-label-points", { type: "geojson", data: labels });
  map.addSource("district-selected-label-point", { type: "geojson", data: oneDistrictLabel(labels, selectedId) });
  if (offline) {
    for (const feature of labels.features) {
      const id = `district-name-${feature.properties.district_id}`;
      if (!map.hasImage(id)) map.addImage(id, offlineLabelImage(feature.properties.district_name, false, dark), { pixelRatio: 2 });
    }
    if (selectedId) {
      const selected = labels.features.find((feature) => feature.properties.district_id === selectedId);
      if (selected) map.addImage("district-selected-name", offlineLabelImage(selected.properties.district_name, true, dark), { pixelRatio: 2 });
    }
  }
  for (const tier of [0, 1, 2]) {
    map.addLayer({
      id: `district-label-tier-${tier}`, type: "symbol", source: "district-label-points", filter: ["==", ["get", "tier"], tier],
      minzoom: tier === 0 ? 0 : tier === 1 ? (compact ? 6.4 : 5.7) : (compact ? 7.8 : 7.2),
      layout: offline ? {
        "icon-image": ["concat", "district-name-", ["get", "district_id"]],
        "icon-allow-overlap": tier === 0, "icon-ignore-placement": false, "icon-padding": tier === 0 ? 7 : 4,
      } : {
        "text-field": ["get", "district_name"], "text-font": ["Noto Sans Regular"],
        "text-size": compact ? ["interpolate", ["linear"], ["zoom"], 4, 9.5, 8, 12] : ["interpolate", ["linear"], ["zoom"], 4, 11, 8, 13],
        "text-max-width": 12, "text-allow-overlap": tier === 0, "text-ignore-placement": false,
        "text-padding": tier === 0 ? (compact ? 10 : 7) : 4,
      },
      paint: offline ? {} : {
        "text-color": dark ? "#f3f9f8" : "#17313a",
        "text-halo-color": dark ? "#071620" : "#f7faf7",
        "text-halo-width": dark ? 1.9 : 1.6,
        "text-halo-blur": 0.25,
      },
    });
  }
  map.addLayer({
    id: "district-selected-label", type: "symbol", source: "district-selected-label-point",
    layout: offline ? { "icon-image": "district-selected-name", "icon-allow-overlap": true } : {
      "text-field": ["get", "district_name"], "text-font": ["Noto Sans Bold"], "text-size": 14,
      "text-allow-overlap": true, "text-padding": 7,
    },
    paint: offline ? {} : { "text-color": dark ? "#ffffff" : "#102832", "text-halo-color": dark ? "#06141e" : "#ffffff", "text-halo-width": 2.4 },
  });
  reportRenderedLabels(map);
}

export function updateDistrictLabels(map: MapLibreMap, geometry: DistrictGeometry | undefined, theme: GeographicStyle): void {
  const source = map.getSource("district-label-points") as GeoJSONSource | undefined;
  if (!source) return;
  const labels = geometry ? districtLabelPoints(geometry) : EMPTY;
  if (!map.getStyle().glyphs) for (const feature of labels.features) {
    const id = `district-name-${feature.properties.district_id}`;
    if (!map.hasImage(id)) map.addImage(id, offlineLabelImage(feature.properties.district_name, false, theme === "dark"), { pixelRatio: 2 });
  }
  source.setData(labels);
  map.getContainer().dataset.districtLabelCount = String(labels.features.length);
  reportRenderedLabels(map);
}

export function updateSelectedDistrictLabel(map: MapLibreMap, geometry: DistrictGeometry | undefined, id: string | null, theme: GeographicStyle): void {
  const source = map.getSource("district-selected-label-point") as GeoJSONSource | undefined;
  if (!source) return;
  const labels = geometry ? districtLabelPoints(geometry) : EMPTY;
  if (!map.getStyle().glyphs && id) {
    const selected = labels.features.find((feature) => feature.properties.district_id === id);
    if (selected) {
      if (map.hasImage("district-selected-name")) map.removeImage("district-selected-name");
      map.addImage("district-selected-name", offlineLabelImage(selected.properties.district_name, true, theme === "dark"), { pixelRatio: 2 });
    }
  }
  source.setData(oneDistrictLabel(labels, id));
}
