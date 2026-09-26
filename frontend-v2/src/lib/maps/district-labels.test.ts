import { describe, expect, it } from "vitest";
import type { Polygon } from "geojson";
import { districtInteriorPoint, districtLabelPoints, oneDistrictLabel, type DistrictGeometry } from "./district-labels";
import { readableGeographyStyle } from "./label-layers";
import type { StyleSpecification } from "maplibre-gl";

const square = (west: number, south: number, east: number, north: number): Polygon => ({
  type: "Polygon", coordinates: [[[west, south], [east, south], [east, north], [west, north], [west, south]]],
});

describe("district cartographic labels", () => {
  it("places a district label inside the validated domain and not in a polygon hole", () => {
    const hole: Polygon = { type: "Polygon", coordinates: [
      [[68, 10], [72, 10], [72, 14], [68, 14], [68, 10]],
      [[69, 11], [71, 11], [71, 13], [69, 13], [69, 11]],
    ] };
    const point = districtInteriorPoint(hole);
    expect(point).not.toBeNull();
    expect(point![0]).toBeGreaterThanOrEqual(68);
    expect(point![0]).toBeLessThanOrEqual(72);
    expect(point![1]).toBeGreaterThanOrEqual(10);
    expect(point![1]).toBeLessThanOrEqual(14);
    expect(point![0] > 69 && point![0] < 71 && point![1] > 11 && point![1] < 13).toBe(false);
  });

  it("returns no point for districts entirely outside the map extent", () => {
    expect(districtInteriorPoint(square(80.5, 23, 81, 24))).toBeNull();
  });

  it("finds an in-domain point for a narrow border intersection", () => {
    const sliver = square(80.11, 21.2, 80.18, 21.21);
    const point = districtInteriorPoint(sliver);
    expect(point).not.toBeNull();
    expect(point![0]).toBeGreaterThan(80.11);
    expect(point![0]).toBeLessThan(80.125);
    expect(point![1]).toBeGreaterThan(21.2);
    expect(point![1]).toBeLessThan(21.21);
  });

  it("uses only authoritative names, caches geometry-derived points, and isolates selection", () => {
    const geometry: DistrictGeometry = { type: "FeatureCollection", features: [
      { type: "Feature", properties: { district_id: "A", district_name: "Real A" }, geometry: square(68, 10, 70, 12) },
      { type: "Feature", properties: { district_id: "B", district_name: "Real B" }, geometry: square(73, 14, 75, 16) },
    ] };
    const first = districtLabelPoints(geometry);
    expect(districtLabelPoints(geometry)).toBe(first);
    expect(first.features.map((feature) => feature.properties.district_name)).toEqual(["Real A", "Real B"]);
    expect(first.features.every((feature) => feature.properties.tier === 0)).toBe(true);
    expect(oneDistrictLabel(first, "B").features.map((feature) => feature.properties.district_id)).toEqual(["B"]);
    expect(oneDistrictLabel(first, "missing").features).toEqual([]);
  });

  it("caps sparse regional and intermediate tiers without altering names", () => {
    const geometry: DistrictGeometry = { type: "FeatureCollection", features: Array.from({ length: 96 }, (_, index) => {
      const west = 68 + index % 12, south = 10 + Math.floor(index / 12);
      return { type: "Feature", properties: { district_id: String(index), district_name: `District ${index}` }, geometry: square(west, south, west + 0.75, south + 0.75) };
    }) };
    const labels = districtLabelPoints(geometry);
    expect(labels.features).toHaveLength(96);
    expect(labels.features.filter((feature) => feature.properties.tier === 0).length).toBeLessThanOrEqual(12);
    expect(labels.features.filter((feature) => feature.properties.tier === 1).length).toBeLessThanOrEqual(60);
    expect(labels.features.every((feature) => feature.properties.district_name.startsWith("District "))).toBe(true);
  });

  it("restyles only supported city/state labels and restrained linework", () => {
    const style: StyleSpecification = { version: 8, sources: {}, layers: [
      { id: "place_city", type: "symbol", source: "x", layout: { "text-field": "city", "text-font": ["Noto Sans Regular"] }, paint: { "text-color": "#666" } },
      { id: "boundary_state", type: "line", source: "x", paint: { "line-color": "#333" } },
      { id: "science", type: "raster", source: "y", paint: { "raster-opacity": 0.78 } },
    ] };
    const result = readableGeographyStyle(style, "dark");
    expect((result.layers[0].paint as { "text-color": string })["text-color"]).toBe("#f3f9f8");
    expect((result.layers[1].paint as { "line-opacity": number })["line-opacity"]).toBe(0.52);
    expect(result.layers[2].paint).toEqual({ "raster-opacity": 0.78 });
  });
});
