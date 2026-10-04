import { describe, expect, it } from "vitest";
import { cellAt, gridFeatures, nearestValidCell, probabilityColor, rainfallColor, rasterCoordinates, rasterPixels, validBounds } from "./grid";
import type { Grid } from "../api/science";

const grid: Grid = {
  crs: "EPSG:4326", shape: [2, 2], latitude_centers: [10, 10.25], longitude_centers: [68, 68.25],
  cell_size_degrees: 0.25, bounds_west_south_east_north: [67.875, 9.875, 68.375, 10.375],
  row_order: "south_to_north", column_order: "west_to_east", mask_policy: "paired valid observation cells",
};

describe("frozen grid rendering", () => {
  it("chooses the nearest valid center cell without using rainfall or observations", () => {
    expect(nearestValidCell([[false, true, false], [false, false, false], [true, false, false]])).toEqual({ row: 0, column: 1 });
    expect(nearestValidCell([[false, false], [false, false]])).toBeNull();
    expect(nearestValidCell([[true], [true, false]])).toBeNull();
  });
  it("uses exact heavy and very-heavy thresholds in the color scale", () => {
    expect(rainfallColor(64.49)).not.toBe(rainfallColor(64.5));
    expect(rainfallColor(115.59)).not.toBe(rainfallColor(115.6));
    expect(probabilityColor(0.05)).not.toBe(probabilityColor(0.049));
  });
  it("maps target-cell centers and excludes east/north outside edges", () => {
    expect(cellAt(grid, 68, 10)).toEqual({ row: 0, column: 0 });
    expect(cellAt(grid, 68.25, 10.25)).toEqual({ row: 1, column: 1 });
    expect(cellAt(grid, 68.375, 10.25)).toBeNull();
    expect(cellAt(grid, 68.25, 10.375)).toBeNull();
  });
  it("never renders masked or null scientific values as zero", () => {
    const features = gridFeatures(grid, [[10, null], [64.5, 115.6]], [[true, true], [false, true]], "rainfall");
    expect(features.features).toHaveLength(2);
    expect(features.features.map((feature) => feature.properties?.value)).toEqual([10, 115.6]);
    expect(features.features[0].geometry.coordinates[0][0]).toEqual([67.875, 9.875]);
  });
  it("rejects any shape mismatch rather than drawing misaligned fields", () => {
    expect(() => gridFeatures(grid, [[1]], [[true]], "rainfall")).toThrow();
    expect(() => gridFeatures(grid, [[1, 2], [3, 4]], [[true], [true]], "rainfall")).toThrow();
  });
  it("places south-to-north arrays north-up with exact image corner order", () => {
    expect(rasterCoordinates(grid)).toEqual([[67.875, 10.375], [68.375, 10.375], [68.375, 9.875], [67.875, 9.875]]);
    const raster = rasterPixels(grid, [[1, 2], [115.6, 20]], [[true, true], [true, true]], "rainfall", "grid");
    expect(raster.width).toBe(2);
    expect([...raster.data.slice(0, 3)]).toEqual([221, 102, 119]); // northwest = south-array row 1, col 0
    expect([...raster.data.slice(8, 11)]).toEqual([49, 92, 120]); // southwest = south-array row 0, col 0
  });
  it("keeps masked pixels transparent and never interpolates across an invalid cell", () => {
    const values = [[0, 100], [0, 100]];
    const mask = [[true, false], [true, true]];
    const raster = rasterPixels(grid, values, mask, "rainfall", "weather");
    const alpha = (x: number, y: number) => raster.data[(y * raster.width + x) * 4 + 3];
    expect(alpha(0, 0)).toBe(255);
    expect(alpha(15, 15)).toBe(0); // southeast source cell is invalid
    const northwest = [...raster.data.slice(0, 3)];
    expect([...raster.data.slice((3 * raster.width + 3) * 4, (3 * raster.width + 3) * 4 + 3)]).toEqual(northwest);
  });
  it("caches identical visualization inputs without changing source values", () => {
    const values = [[0, 1], [2, 3]];
    const mask = [[true, true], [true, true]];
    const original = JSON.stringify(values);
    expect(rasterPixels(grid, values, mask, "probability", "weather")).toBe(rasterPixels(grid, values, mask, "probability", "weather"));
    expect(JSON.stringify(values)).toBe(original);
  });
});

describe("validBounds", () => {
  const grid = { shape: [3, 4], row_order: "south_to_north", column_order: "west_to_east", latitude_centers: [10, 10.25, 10.5], longitude_centers: [70, 70.25, 70.5, 70.75], cell_size_degrees: 0.25, bounds_west_south_east_north: [69.875, 9.875, 70.875, 10.625] } as unknown as Grid;
  it("covers exactly the valid cells, edges included", () => {
    const mask = [[false, false, false, false], [false, true, true, false], [false, false, true, false]];
    expect(validBounds(grid, mask)).toEqual([70.125, 10.125, 70.625, 10.625]);
  });
  it("falls back to the grid bounds when nothing is valid", () => {
    expect(validBounds(grid, [[false, false, false, false], [false, false, false, false], [false, false, false, false]])).toEqual(grid.bounds_west_south_east_north);
  });
});
