import type { Feature, FeatureCollection, MultiPolygon, Point, Polygon, Position } from "geojson";

export const STUDY_BOUNDS: [number, number, number, number] = [67.875, 9.875, 80.125, 22.125];
type DistrictProperties = { district_id: string; district_name: string };
export type DistrictGeometry = FeatureCollection<Polygon | MultiPolygon, DistrictProperties>;
export type DistrictLabel = Feature<Point, DistrictProperties & { tier: number }>;

function inRing(point: Position, ring: Position[]): boolean {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const a = ring[i], b = ring[j];
    if ((a[1] > point[1]) !== (b[1] > point[1]) && point[0] < (b[0] - a[0]) * (point[1] - a[1]) / (b[1] - a[1]) + a[0]) inside = !inside;
  }
  return inside;
}

function insidePolygon(point: Position, rings: Position[][]): boolean {
  return rings.length > 0 && inRing(point, rings[0]) && !rings.slice(1).some((ring) => inRing(point, ring));
}

function segmentDistanceSquared(point: Position, a: Position, b: Position): number {
  const dx = b[0] - a[0], dy = b[1] - a[1];
  const length = dx * dx + dy * dy;
  const t = length ? Math.max(0, Math.min(1, ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy) / length)) : 0;
  return (point[0] - a[0] - t * dx) ** 2 + (point[1] - a[1] - t * dy) ** 2;
}

function clearance(point: Position, rings: Position[][]): number {
  let best = Infinity;
  for (const ring of rings) for (let i = 1; i < ring.length; i++) best = Math.min(best, segmentDistanceSquared(point, ring[i - 1], ring[i]));
  return best;
}

// Bounded point-on-surface search, restricted to the validated map extent.
// It favors broad interior space and never substitutes a polygon centroid that
// could fall in a hole, outside a concavity, or beyond the study domain.
export function districtInteriorPoint(geometry: Polygon | MultiPolygon, bounds = STUDY_BOUNDS): Position | null {
  const polygons = geometry.type === "Polygon" ? [geometry.coordinates] : geometry.coordinates;
  let best: Position | null = null, bestScore = -1;
  for (const rings of polygons) {
    const outer = rings[0];
    if (!outer?.length) continue;
    const west = Math.max(bounds[0], Math.min(...outer.map((p) => p[0])));
    const south = Math.max(bounds[1], Math.min(...outer.map((p) => p[1])));
    const east = Math.min(bounds[2], Math.max(...outer.map((p) => p[0])));
    const north = Math.min(bounds[3], Math.max(...outer.map((p) => p[1])));
    if (west > east || south > north) continue;
    let local: Position | null = null, score = -1;
    let box: [number, number, number, number] = [west, south, east, north];
    // A coarse grid followed by deterministic local refinement is sufficient
    // for label placement; it is not used for area or scientific aggregation.
    for (let pass = 0; pass < 4; pass++) {
      const [x0, y0, x1, y1] = box;
      for (let y = 0; y <= 10; y++) for (let x = 0; x <= 10; x++) {
        const point: Position = [x0 + (x1 - x0) * x / 10, y0 + (y1 - y0) * y / 10];
        if (!insidePolygon(point, rings)) continue;
        const value = clearance(point, rings);
        if (value > score) { local = point; score = value; }
      }
      if (!local) break;
      const radiusX = (x1 - x0) / 5, radiusY = (y1 - y0) / 5;
      box = [Math.max(west, local[0] - radiusX), Math.max(south, local[1] - radiusY), Math.min(east, local[0] + radiusX), Math.min(north, local[1] + radiusY)];
    }
    // Thin polygon intersections can be narrower than the coarse sample grid.
    // Scan at original edge latitudes before conceding that no in-domain
    // interior exists; this keeps tiny coastal/border districts eligible.
    if (!local) {
      const latitudes = [south + (north - south) * 0.5, ...outer.flatMap((p, i) => i ? [(p[1] + outer[i - 1][1]) * 0.5] : [])];
      for (const y of latitudes) {
        if (y <= south || y >= north) continue;
        const crossings: number[] = [];
        for (let i = 1; i < outer.length; i++) {
          const a = outer[i - 1], b = outer[i];
          if ((a[1] > y) !== (b[1] > y)) crossings.push(a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1]));
        }
        crossings.sort((a, b) => a - b);
        for (let i = 1; i < crossings.length; i += 2) {
          const left = Math.max(west, crossings[i - 1]), right = Math.min(east, crossings[i]);
          if (left >= right) continue;
          const point: Position = [(left + right) / 2, y];
          if (insidePolygon(point, rings)) { local = point; score = clearance(point, rings); break; }
        }
        if (local) break;
      }
    }
    if (local && score > bestScore) { best = local; bestScore = score; }
  }
  return best;
}

const cache = new WeakMap<DistrictGeometry, FeatureCollection<Point, DistrictLabel["properties"]>>();
export function districtLabelPoints(geometry: DistrictGeometry): FeatureCollection<Point, DistrictLabel["properties"]> {
  const existing = cache.get(geometry);
  if (existing) return existing;
  const candidates = geometry.features.flatMap((feature) => {
    const point = districtInteriorPoint(feature.geometry);
    return point ? [{ point, district_id: feature.properties.district_id, district_name: feature.properties.district_name }] : [];
  });
  // Spatial thinning is deterministic and geometry-only. Collision detection
  // then makes the final viewport-dependent choice in MapLibre.
  const tiers = new Map<string, number>();
  const anchors: Position[] = [], middle: Position[] = [];
  const center: Position = [(STUDY_BOUNDS[0] + STUDY_BOUNDS[2]) / 2, (STUDY_BOUNDS[1] + STUDY_BOUNDS[3]) / 2];
  const remaining = [...candidates];
  while (anchors.length < 12 && remaining.length) {
    const nearestDistance = (point: Position) => Math.min(...(anchors.length ? anchors : [center]).map((p) => (p[0] - point[0]) ** 2 + (p[1] - point[1]) ** 2));
    // Seed at the domain center, then choose the farthest unrepresented area.
    remaining.sort((a, b) => (anchors.length ? nearestDistance(b.point) - nearestDistance(a.point) : nearestDistance(a.point) - nearestDistance(b.point)) || a.district_id.localeCompare(b.district_id));
    const item = remaining.shift()!;
    if (!distantFrom(item.point, anchors, 1.65)) continue;
    tiers.set(item.district_id, 0); anchors.push(item.point); middle.push(item.point);
  }
  for (const item of candidates) {
    if (tiers.has(item.district_id)) continue;
    if (middle.length < 60 && distantFrom(item.point, middle, 1.05)) { tiers.set(item.district_id, 1); middle.push(item.point); }
  }
  const result: FeatureCollection<Point, DistrictLabel["properties"]> = { type: "FeatureCollection", features: candidates.map((item) => ({
    type: "Feature", geometry: { type: "Point", coordinates: item.point },
    properties: { district_id: item.district_id, district_name: item.district_name, tier: tiers.get(item.district_id) ?? 2 },
  })) };
  cache.set(geometry, result);
  return result;
}

function distantFrom(point: Position, points: Position[], minimum: number): boolean {
  return points.every((p) => (p[0] - point[0]) ** 2 + (p[1] - point[1]) ** 2 >= minimum ** 2);
}

export function oneDistrictLabel(labels: FeatureCollection<Point, DistrictLabel["properties"]>, id: string | null): FeatureCollection<Point, DistrictLabel["properties"]> {
  return { type: "FeatureCollection", features: id ? labels.features.filter((feature) => feature.properties.district_id === id) : [] };
}
