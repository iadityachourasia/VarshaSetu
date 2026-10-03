import { describe, expect, it } from "vitest";
import type { Grid } from "@/lib/api/science";
import { DECISION_BINS, DIM_ALPHA, PROBABILITY_BINS, RAINFALL_BINS, emphasisFor, emphasisKind, inBin } from "./emphasis";
import { rasterPixels } from "./grid";

const grid = { shape: [2, 3], row_order: "south_to_north", column_order: "west_to_east", latitude_centers: [10, 10.25], longitude_centers: [70, 70.25, 70.5], cell_size_degrees: 0.25, bounds_west_south_east_north: [69.875, 9.875, 70.625, 10.375] } as unknown as Grid;
const values = [[0, 3, 12], [30, 70, 130]];
const mask = [[true, true, true], [true, true, false]];

describe("legend classes", () => {
  it("partition the whole axis with no gap and no overlap", () => {
    for (const bins of [RAINFALL_BINS, PROBABILITY_BINS, DECISION_BINS]) {
      expect(bins[0].lo).toBe(-Infinity);
      expect(bins[bins.length - 1].hi).toBe(Infinity);
      for (let index = 1; index < bins.length; index++) expect(bins[index].lo).toBe(bins[index - 1].hi);
    }
  });
  it("put every value in exactly one class", () => {
    for (const value of [0, 0.099, 0.1, 4.99, 5, 64.49, 64.5, 115.59, 115.6, 400]) expect(RAINFALL_BINS.filter((bin) => inBin(value, bin.lo, bin.hi))).toHaveLength(1);
  });
  it("only a legend of the same kind of quantity applies to a map", () => {
    const rain = { kind: "rainfall" as const, lo: 5, hi: 20 };
    expect(emphasisFor(rain, "rainfall")).toBe(rain);
    expect(emphasisFor(rain, "probability")).toBeNull();
    expect(emphasisFor(null, "rainfall")).toBeNull();
    expect(emphasisKind("u850")).toBeNull();
  });
});

describe("emphasis dims by alpha only", () => {
  const plain = rasterPixels(grid, values, mask, "rainfall", "grid");
  const dimmed = rasterPixels(grid, values, mask, "rainfall", "grid", { kind: "rainfall", lo: 20, hi: 64.5 });
  it("keeps every colour channel and every masked cell exactly as without emphasis", () => {
    expect(dimmed.data.length).toBe(plain.data.length);
    for (let offset = 0; offset < plain.data.length; offset += 4) {
      expect(dimmed.data[offset]).toBe(plain.data[offset]);
      expect(dimmed.data[offset + 1]).toBe(plain.data[offset + 1]);
      expect(dimmed.data[offset + 2]).toBe(plain.data[offset + 2]);
      if (plain.data[offset + 3] === 0) expect(dimmed.data[offset + 3]).toBe(0);
    }
  });
  it("leaves the emphasised class opaque and dims the rest", () => {
    const alphas = new Map<number, number>();
    // Row 0 of the picture is the northern grid row (30, 70, masked); the 30 mm cell there is the only one inside 20 to <64.5 mm.
    for (let y = 0; y < 2; y++) for (let x = 0; x < 3; x++) alphas.set(y * 3 + x, dimmed.data[(y * 3 + x) * 4 + 3]);
    expect(alphas.get(0)).toBe(255);
    expect([...alphas.entries()].filter(([index, alpha]) => index !== 0 && index !== 2 && alpha === DIM_ALPHA)).toHaveLength(4);
    expect(alphas.get(2)).toBe(0);
  });
  it("does not disturb the cached picture of the data itself", () => {
    expect(rasterPixels(grid, values, mask, "rainfall", "grid")).toBe(plain);
    expect(plain.data[0 * 4 + 3]).toBe(255);
  });
});
