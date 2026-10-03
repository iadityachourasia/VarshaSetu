"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { type GeoJSONSource, type Map as MapLibreMap } from "maplibre-gl";
import type { FeatureCollection } from "geojson";
import type { District, Geometry } from "@/lib/api/science";
import { firstLabelLayer } from "@/lib/maps/basemap";
import { installDistrictLabels, updateSelectedDistrictLabel } from "@/lib/maps/label-layers";
import type { DistrictGeometry } from "@/lib/maps/district-labels";
import { MapAttribution } from "@/components/maps/map-attribution";
import { LocatorInset } from "@/components/maps/locator-inset";
import { rainfallColor } from "@/lib/maps/grid";
import { useMapSettings } from "@/components/maps/map-settings";
import { useWeatherMap } from "@/components/maps/use-weather-map";

const DOMAIN: [number, number, number, number] = [67.875, 9.875, 80.125, 22.125];

export default function DistrictMap({ geometry, districts, selectedId, onSelect, onReady, colorFor = rainfallColor }: {
  geometry: Geometry["geometry"]; districts: District[]; selectedId: string | null;
  onSelect: (id: string) => void; onReady?: (map: MapLibreMap | null) => void;
  /** Colour scale for the polygon value carried in `corrected_mean_mm` (defaults to the rainfall scale). */
  colorFor?: (value: number) => string;
}) {
  const settings = useMapSettings();
  const element = useRef<HTMLDivElement>(null);
  const selectRef = useRef(onSelect);
  const readyRef = useRef(onReady);
  const [hoveredName, setHoveredName] = useState<string | null>(null);
  const data = useMemo(() => {
    const byId = new Map(districts.map((item) => [item.district_id, item]));
    return { type: "FeatureCollection", features: geometry.features.map((feature) => {
      const district = byId.get(feature.properties.district_id);
      return { ...feature, properties: { ...feature.properties, corrected_mean_mm: district?.corrected_mean_mm ?? null, color: district ? colorFor(district.corrected_mean_mm) : "#566a72" } };
    }) } as FeatureCollection;
  }, [geometry, districts, colorFor]);
  useEffect(() => { selectRef.current = onSelect; readyRef.current = onReady; }, [onSelect, onReady]);

  const installLayers = useCallback((map: MapLibreMap) => {
    const before = firstLabelLayer(map.getStyle());
    map.addSource("district-choropleth", { type: "geojson", data });
    map.addLayer({ id: "district-fill", type: "fill", source: "district-choropleth", paint: { "fill-color": ["get", "color"], "fill-opacity": 0.75 } }, before);
    map.addLayer({ id: "district-line", type: "line", source: "district-choropleth", layout: { visibility: settings.boundaries ? "visible" : "none" }, paint: { "line-color": settings.geographicStyle === "dark" ? "#d7e8e5" : "#365d65", "line-opacity": 0.4, "line-width": 0.65 } }, before);
    map.addLayer({ id: "district-hover", type: "line", source: "district-choropleth", filter: ["==", ["get", "district_id"], ""], paint: { "line-color": "#f4f7e6", "line-width": 1.5 } });
    map.addLayer({ id: "district-selected", type: "line", source: "district-choropleth", filter: ["==", ["get", "district_id"], selectedId ?? ""], paint: { "line-color": "#ffffff", "line-width": 3 } });
    installDistrictLabels(map, geometry as DistrictGeometry, settings.geographicStyle, selectedId);
    // Local choropleth readiness must not depend on an external tile server idling.
    if (element.current) element.current.dataset.ready = "true";
  }, [data, geometry, selectedId, settings.boundaries, settings.geographicStyle]);

  const { mapRef, status } = useWeatherMap({
    element, bounds: DOMAIN, geometry: geometry as FeatureCollection,
    geographicStyle: settings.geographicStyle, onStyleReady: installLayers,
    onReady: (map) => readyRef.current?.(map),
  });

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const click = (event: { features?: Array<{ properties?: Record<string, unknown> }> }) => {
      const id = event.features?.[0]?.properties?.district_id;
      if (typeof id === "string" && districts.some((item) => item.district_id === id)) selectRef.current(id);
    };
    const hover = (event: { features?: Array<{ properties?: Record<string, unknown> }> }) => {
      const id = event.features?.[0]?.properties?.district_id;
      const name = event.features?.[0]?.properties?.district_name;
      if (map.getLayer("district-hover")) map.setFilter("district-hover", ["==", ["get", "district_id"], typeof id === "string" ? id : ""]);
      setHoveredName(typeof name === "string" ? name : null);
      map.getCanvas().style.cursor = typeof id === "string" ? "pointer" : "";
    };
    const leave = () => { if (map.getLayer("district-hover")) map.setFilter("district-hover", ["==", ["get", "district_id"], ""]); setHoveredName(null); map.getCanvas().style.cursor = ""; };
    map.on("click", "district-fill", click); map.on("mousemove", "district-fill", hover); map.on("mouseleave", "district-fill", leave);
    return () => { map.off("click", "district-fill", click); map.off("mousemove", "district-fill", hover); map.off("mouseleave", "district-fill", leave); };
  }, [districts, mapRef]);
  useEffect(() => { (mapRef.current?.getSource("district-choropleth") as GeoJSONSource | undefined)?.setData(data); }, [data, mapRef]);
  useEffect(() => { const map = mapRef.current; if (map?.getLayer("district-selected")) map.setFilter("district-selected", ["==", ["get", "district_id"], selectedId ?? ""]); }, [selectedId, mapRef]);
  useEffect(() => { const map = mapRef.current; if (map) updateSelectedDistrictLabel(map, geometry as DistrictGeometry, selectedId, settings.geographicStyle); }, [selectedId, geometry, mapRef, settings.geographicStyle]);
  useEffect(() => { const map = mapRef.current; if (map?.getLayer("district-line")) map.setLayoutProperty("district-line", "visibility", settings.boundaries ? "visible" : "none"); }, [settings.boundaries, mapRef]);
  return <div className="district-map-frame"><div className="district-map" ref={element} role="img" aria-label="District polygons colored by case-specific corrected mean rainfall. Use the district table for keyboard selection." /><LocatorInset bounds={DOMAIN} theme={settings.geographicStyle} /><MapAttribution status={status} />{hoveredName ? <span className="district-map-hover">{hoveredName}</span> : null}{status === "offline" ? <span className="map-offline-badge">Offline geography</span> : null}{status === "loading" ? <span className="map-offline-badge">Loading geography…</span> : null}</div>;
}
