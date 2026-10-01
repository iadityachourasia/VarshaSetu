import { describe, expect, it } from "vitest";
import { cellPolygons, contourFeatures, contourLevels, contourSegments, joinSegments, lineMidpoint, niceInterval, valueRange, windArrows, type Matrix } from "./geometry";

const lats = Array.from({ length: 21 }, (_, i) => 10 + i * 0.5);
const lons = Array.from({ length: 21 }, (_, j) => 60 + j * 0.5);
const field = (f: (lon: number, lat: number) => number): Matrix => lats.map((lat) => lons.map((lon) => f(lon, lat)));

describe("contour levels", () => {
  it("chooses a nice interval and exact multiples inside the range", () => {
    expect(niceInterval(5820, 5920, 10)).toBe(10);
    expect(niceInterval(0, 100, 10)).toBe(10);
    expect(niceInterval(0, 7, 7)).toBe(1);
    expect(niceInterval(3, 3)).toBe(1);
    expect(contourLevels(5821, 5897, 20)).toEqual([5840, 5860, 5880]);
    expect(contourLevels(1000.5, 1004.5, 2)).toEqual([1002, 1004]);
    expect(contourLevels(5, 1, 2)).toEqual([]);
  });
  it("finds the data range ignoring missing values", () => {
    expect(valueRange([[1, null], [Number.NaN, 4]])).toEqual({ min: 1, max: 4 });
    expect(valueRange([[null]])).toBeNull();
  });
});

describe("marching squares", () => {
  it("draws a linear field's contour as a straight line at the exact coordinate", () => {
    const segments = contourSegments(field((lon) => lon), lats, lons, 65.25);
    expect(segments).toHaveLength(lats.length - 1);
    for (const [a, b] of segments) { expect(a[0]).toBeCloseTo(65.25, 10); expect(b[0]).toBeCloseTo(65.25, 10); }
    const lines = joinSegments(segments);
    expect(lines).toHaveLength(1);
    expect(lines[0]).toHaveLength(lats.length);
  });

  it("closes the contour of a bowl around its centre at the right radius", () => {
    const bowl = field((lon, lat) => (lon - 65) ** 2 + (lat - 15) ** 2);
    const [feature] = contourFeatures(bowl, lats, lons, [4]);
    expect(feature.lines).toHaveLength(1);
    const ring = feature.lines[0];
    expect(ring[0][0]).toBeCloseTo(ring[ring.length - 1][0], 9);
    expect(ring[0][1]).toBeCloseTo(ring[ring.length - 1][1], 9);
    for (const [lon, lat] of ring) {
      const radius = Math.hypot(lon - 65, lat - 15);
      expect(radius).toBeGreaterThan(1.9);
      expect(radius).toBeLessThan(2.05);
    }
  });

  it("never draws through a missing value and gives nothing when the level is outside the data", () => {
    const holey = field((lon) => lon);
    holey[10][10] = null;
    holey[5][5] = Number.NaN;
    const segments = contourSegments(holey, lats, lons, 65.25);
    expect(segments.length).toBeLessThan(lats.length - 1);
    expect(contourSegments(field((lon) => lon), lats, lons, 500)).toEqual([]);
  });

  it("resolves a saddle without crossing contours and keeps every segment on a cell edge", () => {
    const saddle: Matrix = [[1, 0], [0, 1]];
    const segments = contourSegments(saddle, [0, 1], [0, 1], 0.5);
    expect(segments).toHaveLength(2);
    for (const [a, b] of segments) for (const [lon, lat] of [a, b]) expect(lon >= 0 && lon <= 1 && lat >= 0 && lat <= 1).toBe(true);
  });

  it("anchors a label on the polyline by length", () => {
    const [mid] = [lineMidpoint([[0, 0], [10, 0]])];
    expect(mid).toEqual([5, 0]);
    expect(lineMidpoint([[0, 0], [2, 0], [2, 2]])).toEqual([2, 0]);
  });
});

describe("wind arrows", () => {
  const u = field(() => 8), v = field(() => 0);
  it("points the way the wind blows and reports its speed and bearing", () => {
    const [arrow] = windArrows(u, v, lats, lons, { stride: 100, degreesPerMetreSecond: 0.1 });
    expect(arrow.speed).toBe(8);
    expect(arrow.direction).toBeCloseTo(90, 9); // a westerly blows toward the east
    expect(arrow.line[1][0]).toBeGreaterThan(arrow.line[0][0]);
    expect(arrow.line[1][1]).toBeCloseTo(arrow.line[0][1], 9);
    const [south] = windArrows(field(() => 0), field(() => 5), lats, lons, { stride: 100, degreesPerMetreSecond: 0.1 });
    expect(south.direction).toBeCloseTo(0, 9);
    expect(south.line[1][1]).toBeGreaterThan(south.line[0][1]);
    const [north] = windArrows(field(() => 0), field(() => -5), lats, lons, { stride: 100, degreesPerMetreSecond: 0.1 });
    expect(north.direction).toBeCloseTo(180, 9);
  });
  it("keeps the true direction in map space: longitude is stretched by 1/cos(latitude)", () => {
    const [arrow] = windArrows(field(() => 4), field(() => 4), [60], [60], { stride: 1, degreesPerMetreSecond: 0.1 });
    const dx = arrow.line[1][0] - arrow.line[0][0], dy = arrow.line[1][1] - arrow.line[0][1];
    expect(dx / dy).toBeCloseTo(1 / Math.cos((60 * Math.PI) / 180), 9);
  });
  it("subsamples by the stride, drops calm and missing points, and draws a five-point arrow head", () => {
    const all = windArrows(u, v, lats, lons, { stride: 1, degreesPerMetreSecond: 0.05 });
    expect(all).toHaveLength(lats.length * lons.length);
    expect(windArrows(u, v, lats, lons, { stride: 2, degreesPerMetreSecond: 0.05 })).toHaveLength(11 * 11);
    expect(windArrows(field(() => 0.1), field(() => 0.1), lats, lons, { stride: 1, degreesPerMetreSecond: 0.05 })).toEqual([]);
    const withHole = field(() => 5);
    withHole[0][0] = null;
    expect(windArrows(withHole, v, lats, lons, { stride: 1, degreesPerMetreSecond: 0.05 })).toHaveLength(lats.length * lons.length - 1);
    expect(all[0].line).toHaveLength(5);
  });
});

describe("shaded cells", () => {
  it("makes one square per valid cell, centred on its coordinate", () => {
    const values: Matrix = [[1, null], [3, 4]];
    const cells = cellPolygons(values, [10, 10.5], [60, 60.5], 0.5);
    expect(cells).toHaveLength(3);
    expect(cells[0].ring).toEqual([[59.75, 9.75], [60.25, 9.75], [60.25, 10.25], [59.75, 10.25], [59.75, 9.75]]);
    expect(cells.map((c) => c.value)).toEqual([1, 3, 4]);
  });
});
