// Pure geometry for the synoptic chart: contour lines (marching squares), contour levels, wind arrows and shaded cells.
// Everything here is derived from the frozen forecast values and their coordinates; nothing is smoothed, filled or invented.
// A cell with a missing value (null or NaN) never produces geometry.

export type Matrix = (number | null)[][];
export type Point = [number, number]; // [longitude, latitude]

const finite = (value: number | null | undefined): value is number => typeof value === "number" && Number.isFinite(value);

/** A "nice" contour interval (1, 2, 2.5 or 5 times a power of ten) giving roughly `target` lines across the range. */
export function niceInterval(min: number, max: number, target = 10): number {
  const span = max - min;
  if (!(span > 0) || !(target > 0)) return 1;
  const raw = span / target;
  const magnitude = 10 ** Math.floor(Math.log10(raw));
  const normalised = raw / magnitude;
  const step = normalised <= 1 ? 1 : normalised <= 2 ? 2 : normalised <= 2.5 ? 2.5 : normalised <= 5 ? 5 : 10;
  return step * magnitude;
}

/** Multiples of `interval` that fall inside [min, max]. */
export function contourLevels(min: number, max: number, interval: number): number[] {
  if (!(interval > 0) || !(max >= min)) return [];
  const first = Math.ceil(min / interval - 1e-9);
  const last = Math.floor(max / interval + 1e-9);
  const levels: number[] = [];
  for (let k = first; k <= last; k++) levels.push(Number((k * interval).toFixed(10)));
  return levels;
}

export function valueRange(values: Matrix): { min: number; max: number } | null {
  let min = Infinity;
  let max = -Infinity;
  for (const row of values) for (const value of row) if (finite(value)) { if (value < min) min = value; if (value > max) max = value; }
  return min <= max ? { min, max } : null;
}

function edge(a: Point, b: Point, va: number, vb: number, level: number): Point {
  const t = vb === va ? 0.5 : (level - va) / (vb - va);
  return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];
}

/**
 * Line segments of the `level` contour by marching squares on the cell corners. Corner values at exactly the level are treated as
 * slightly above it so that every contour is a closed or boundary-ending curve without zero-length artefacts. Ambiguous saddle
 * cells are resolved by the mean of their four corners. Returns segments as [start, end] pairs of [lon, lat].
 */
export function contourSegments(values: Matrix, latitudes: number[], longitudes: number[], level: number): [Point, Point][] {
  const segments: [Point, Point][] = [];
  for (let i = 0; i + 1 < latitudes.length; i++) {
    for (let j = 0; j + 1 < longitudes.length; j++) {
      const v00 = values[i]?.[j], v01 = values[i]?.[j + 1], v11 = values[i + 1]?.[j + 1], v10 = values[i + 1]?.[j];
      if (!finite(v00) || !finite(v01) || !finite(v11) || !finite(v10)) continue;
      const p00: Point = [longitudes[j], latitudes[i]], p01: Point = [longitudes[j + 1], latitudes[i]];
      const p11: Point = [longitudes[j + 1], latitudes[i + 1]], p10: Point = [longitudes[j], latitudes[i + 1]];
      const above = (value: number) => value >= level;
      const index = (above(v00) ? 1 : 0) | (above(v01) ? 2 : 0) | (above(v11) ? 4 : 0) | (above(v10) ? 8 : 0);
      if (index === 0 || index === 15) continue;
      const bottom = () => edge(p00, p01, v00, v01, level); // between 00 and 01
      const right = () => edge(p01, p11, v01, v11, level);
      const top = () => edge(p10, p11, v10, v11, level);
      const left = () => edge(p00, p10, v00, v10, level);
      const mean = (v00 + v01 + v11 + v10) / 4;
      switch (index) {
        case 1: case 14: segments.push([left(), bottom()]); break;
        case 2: case 13: segments.push([bottom(), right()]); break;
        case 3: case 12: segments.push([left(), right()]); break;
        case 4: case 11: segments.push([right(), top()]); break;
        case 6: case 9: segments.push([bottom(), top()]); break;
        case 7: case 8: segments.push([left(), top()]); break;
        case 5: // 00 and 11 above: saddle
          if (mean >= level) { segments.push([left(), top()]); segments.push([bottom(), right()]); } else { segments.push([left(), bottom()]); segments.push([right(), top()]); }
          break;
        case 10: // 01 and 10 above: saddle
          if (mean >= level) { segments.push([left(), bottom()]); segments.push([right(), top()]); } else { segments.push([left(), top()]); segments.push([bottom(), right()]); }
          break;
        default: break;
      }
    }
  }
  return segments;
}

const key = (point: Point) => `${point[0].toFixed(6)},${point[1].toFixed(6)}`;

/** Joins segments that share end points into polylines (each segment used once). */
export function joinSegments(segments: [Point, Point][]): Point[][] {
  const byEnd = new Map<string, number[]>();
  segments.forEach((segment, index) => {
    for (const end of segment) { const k = key(end); byEnd.set(k, [...(byEnd.get(k) ?? []), index]); }
  });
  const used = new Array(segments.length).fill(false);
  const lines: Point[][] = [];
  const extend = (line: Point[], atEnd: boolean) => {
    for (;;) {
      const tip = atEnd ? line[line.length - 1] : line[0];
      const next = (byEnd.get(key(tip)) ?? []).find((candidate) => !used[candidate]);
      if (next === undefined) return;
      used[next] = true;
      const [a, b] = segments[next];
      const other = key(a) === key(tip) ? b : a;
      if (atEnd) line.push(other); else line.unshift(other);
    }
  };
  segments.forEach((segment, index) => {
    if (used[index]) return;
    used[index] = true;
    const line: Point[] = [segment[0], segment[1]];
    extend(line, true);
    extend(line, false);
    lines.push(line);
  });
  return lines;
}

export function lineLength(line: Point[]): number {
  let total = 0;
  for (let i = 1; i < line.length; i++) total += Math.hypot(line[i][0] - line[i - 1][0], line[i][1] - line[i - 1][1]);
  return total;
}

/** Midpoint along a polyline by length, used to anchor a contour label. */
export function lineMidpoint(line: Point[]): Point {
  const half = lineLength(line) / 2;
  let walked = 0;
  for (let i = 1; i < line.length; i++) {
    const step = Math.hypot(line[i][0] - line[i - 1][0], line[i][1] - line[i - 1][1]);
    if (walked + step >= half && step > 0) {
      const t = (half - walked) / step;
      return [line[i - 1][0] + (line[i][0] - line[i - 1][0]) * t, line[i - 1][1] + (line[i][1] - line[i - 1][1]) * t];
    }
    walked += step;
  }
  return line[0];
}

export type ContourFeature = { level: number; lines: Point[][] };

export function contourFeatures(values: Matrix, latitudes: number[], longitudes: number[], levels: number[]): ContourFeature[] {
  return levels.map((level) => ({ level, lines: joinSegments(contourSegments(values, latitudes, longitudes, level)) })).filter((feature) => feature.lines.length > 0);
}

export type WindArrow = { speed: number; direction: number; line: Point[] };

/**
 * One arrow per `stride`-th grid point. Web-Mercator is locally conformal, so a physical displacement (u east, v north) is drawn
 * as (u / cos(latitude), v) in degrees times `degreesPerMetreSecond`: the arrow points exactly where the wind blows. Calm points
 * (speed below `minimumSpeed`) get no arrow. `direction` is the meteorological "toward" bearing in degrees clockwise from north.
 */
export function windArrows(u: Matrix, v: Matrix, latitudes: number[], longitudes: number[], options: { stride: number; degreesPerMetreSecond: number; minimumSpeed?: number }): WindArrow[] {
  const { stride, degreesPerMetreSecond, minimumSpeed = 0.5 } = options;
  const arrows: WindArrow[] = [];
  for (let i = 0; i < latitudes.length; i += stride) {
    for (let j = 0; j < longitudes.length; j += stride) {
      const east = u[i]?.[j], north = v[i]?.[j];
      if (!finite(east) || !finite(north)) continue;
      const speed = Math.hypot(east, north);
      if (speed < minimumSpeed) continue;
      const cos = Math.cos((latitudes[i] * Math.PI) / 180);
      const dx = (east / cos) * degreesPerMetreSecond;
      const dy = north * degreesPerMetreSecond;
      const tail: Point = [longitudes[j] - dx / 2, latitudes[i] - dy / 2];
      const tip: Point = [longitudes[j] + dx / 2, latitudes[i] + dy / 2];
      // arrow head: two barbs 150 degrees either side of the shaft, 35 percent of its length (in map space, hence conformal)
      const angle = Math.atan2(dy, dx);
      const barb = Math.hypot(dx, dy) * 0.35;
      const left: Point = [tip[0] + barb * Math.cos(angle + (150 * Math.PI) / 180), tip[1] + barb * Math.sin(angle + (150 * Math.PI) / 180)];
      const right: Point = [tip[0] + barb * Math.cos(angle - (150 * Math.PI) / 180), tip[1] + barb * Math.sin(angle - (150 * Math.PI) / 180)];
      arrows.push({ speed, direction: (((Math.atan2(east, north) * 180) / Math.PI) + 360) % 360, line: [tail, tip, left, tip, right] });
    }
  }
  return arrows;
}

export type CellPolygon = { value: number; ring: Point[] };

/** One square per grid cell, centred on its coordinate, for shaded display. Missing values give no cell. */
export function cellPolygons(values: Matrix, latitudes: number[], longitudes: number[], spacing: number): CellPolygon[] {
  const half = spacing / 2;
  const cells: CellPolygon[] = [];
  for (let i = 0; i < latitudes.length; i++) {
    for (let j = 0; j < longitudes.length; j++) {
      const value = values[i]?.[j];
      if (!finite(value)) continue;
      const w = longitudes[j] - half, e = longitudes[j] + half, s = latitudes[i] - half, n = latitudes[i] + half;
      cells.push({ value, ring: [[w, s], [e, s], [e, n], [w, n], [w, s]] });
    }
  }
  return cells;
}
