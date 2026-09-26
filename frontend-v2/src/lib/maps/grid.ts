import type { FeatureCollection, Polygon } from "geojson";
import type { Grid } from "@/lib/api/science";

export type CellSelection = { row: number; column: number };
export type Palette = "rainfall" | "probability" | "error-difference" | "u850" | "v850" | "q700" | "z500" | "mslp" | "pwat";
export type RasterMode = "weather" | "grid";
export type RasterPixels = { width: number; height: number; data: Uint8ClampedArray<ArrayBuffer> };

export function nearestValidCell(mask: boolean[][]): CellSelection | null {
  const rows = mask.length;
  const columns = mask[0]?.length ?? 0;
  if (!rows || !columns || mask.some((row) => row.length !== columns)) return null;
  const centerRow = (rows - 1) / 2;
  const centerColumn = (columns - 1) / 2;
  let best: CellSelection | null = null;
  let distance = Infinity;
  for (let row = 0; row < rows; row++) for (let column = 0; column < columns; column++) {
    if (!mask[row][column]) continue;
    const candidate = (row - centerRow) ** 2 + (column - centerColumn) ** 2;
    if (candidate < distance) { best = { row, column }; distance = candidate; }
  }
  return best;
}

const cache = new WeakMap<object, WeakMap<object, Map<string, RasterPixels>>>();
const rainStops: [number, string][] = [[0, "#142a37"], [0.1, "#315c78"], [5, "#3d8db5"], [20, "#58bad0"], [40, "#79d1bf"], [64.5, "#e6a854"], [115.6, "#dd6677"], [200, "#a94769"]];
const probabilityStops: [number, string][] = [[0, "#292647"], [0.05, "#493f81"], [0.15, "#465ca2"], [0.3, "#3f9a9f"], [0.5, "#94c478"], [0.7, "#dcc968"], [1, "#f1e18c"]];
const fieldStops: Record<Exclude<Palette, "rainfall" | "probability">, [number, string][]> = {
  "error-difference": [[-100, "#327eac"], [-40, "#59a9c8"], [-10, "#a8d5d4"], [0, "#d9ded9"], [10, "#ebbe89"], [40, "#db835f"], [100, "#a74755"]],
  u850: [[-20, "#484b91"], [-10, "#5f83bb"], [0, "#cedbd6"], [10, "#e0ae75"], [25, "#ac5d58"]],
  v850: [[-20, "#484b91"], [-10, "#5f83bb"], [0, "#cedbd6"], [10, "#e0ae75"], [25, "#ac5d58"]],
  q700: [[0, "#293e57"], [0.003, "#326f93"], [0.007, "#53a7af"], [0.011, "#b9c877"], [0.016, "#eac778"]],
  z500: [[5750, "#4c5890"], [5800, "#477ca8"], [5850, "#9dbabd"], [5900, "#e2c485"], [5950, "#c78462"]],
  mslp: [[97000, "#45579a"], [99000, "#5d9dbb"], [100000, "#c4d5ca"], [101000, "#d8bf81"], [103000, "#b76b58"]],
  pwat: [[0, "#293e57"], [20, "#326f93"], [40, "#53a7af"], [60, "#b9c877"], [90, "#eac778"]],
};

function rgb(hex: string): [number, number, number] {
  return [1, 3, 5].map((offset) => Number.parseInt(hex.slice(offset, offset + 2), 16)) as [number, number, number];
}

export function smoothColor(value: number, palette: Palette): [number, number, number] {
  const stops = palette === "rainfall" ? rainStops : palette === "probability" ? probabilityStops : fieldStops[palette];
  if (value <= stops[0][0]) return rgb(stops[0][1]);
  for (let index = 1; index < stops.length; index++) {
    const [limit, color] = stops[index];
    if (value <= limit) {
      const [previous, previousColor] = stops[index - 1];
      const fraction = (value - previous) / (limit - previous);
      const from = rgb(previousColor), to = rgb(color);
      return from.map((channel, part) => Math.round(channel + (to[part] - channel) * fraction)) as [number, number, number];
    }
  }
  return rgb(stops[stops.length - 1][1]);
}

export function rainfallColor(value: number): string {
  if (value < 0.1) return "#142a37";
  if (value < 5) return "#315c78";
  if (value < 20) return "#3d8db5";
  if (value < 40) return "#58bad0";
  if (value < 64.5) return "#79d1bf";
  if (value < 115.6) return "#e6a854";
  return "#dd6677";
}

export function probabilityColor(value: number): string {
  if (value < 0.05) return "#292647";
  if (value < 0.15) return "#493f81";
  if (value < 0.3) return "#465ca2";
  if (value < 0.5) return "#3f9a9f";
  if (value < 0.7) return "#94c478";
  if (value < 0.9) return "#dcc968";
  return "#f1e18c";
}

export function cellAt(grid: Grid, longitude: number, latitude: number): CellSelection | null {
  const [west, south, east, north] = grid.bounds_west_south_east_north;
  if (longitude < west || longitude >= east || latitude < south || latitude >= north) return null;
  const column = Math.floor((longitude - west) / grid.cell_size_degrees);
  const row = Math.floor((latitude - south) / grid.cell_size_degrees);
  return row >= 0 && row < grid.shape[0] && column >= 0 && column < grid.shape[1] ? { row, column } : null;
}

export function rasterCoordinates(grid: Grid): [[number, number], [number, number], [number, number], [number, number]] {
  const [west, south, east, north] = grid.bounds_west_south_east_north;
  return [[west, north], [east, north], [east, south], [west, south]];
}

export function rasterPixels(grid: Grid, values: (number | null)[][], mask: boolean[][], palette: Palette, mode: RasterMode): RasterPixels {
  const [rows, columns] = grid.shape;
  if (grid.row_order !== "south_to_north" || grid.column_order !== "west_to_east" || values.length !== rows || mask.length !== rows || grid.latitude_centers.length !== rows || grid.longitude_centers.length !== columns) {
    throw new Error("Grid orientation or dimensions do not match the frozen science contract");
  }
  for (let row = 0; row < rows; row++) if (values[row].length !== columns || mask[row].length !== columns) throw new Error("Grid row dimensions are invalid");
  const scale = mode === "weather" ? 8 : 1;
  const key = `${palette}:${mode}:${rows}:${columns}`;
  let byMask = cache.get(values);
  if (!byMask) { byMask = new WeakMap(); cache.set(values, byMask); }
  let byKey = byMask.get(mask);
  if (!byKey) { byKey = new Map(); byMask.set(mask, byKey); }
  const found = byKey.get(key);
  if (found) return found;
  const width = columns * scale, height = rows * scale;
  const data = new Uint8ClampedArray(width * height * 4);
  const usable = (row: number, column: number) => row >= 0 && row < rows && column >= 0 && column < columns && mask[row][column] && values[row][column] != null && Number.isFinite(values[row][column]);
  for (let y = 0; y < height; y++) {
    const nearestRow = rows - 1 - Math.floor(y / scale);
    const fractionalNorthRow = (y + 0.5) / scale - 0.5;
    const north0 = Math.max(0, Math.min(rows - 1, Math.floor(fractionalNorthRow)));
    const north1 = Math.max(0, Math.min(rows - 1, north0 + 1));
    const row0 = rows - 1 - north0, row1 = rows - 1 - north1;
    const rowFraction = Math.max(0, Math.min(1, fractionalNorthRow - north0));
    for (let x = 0; x < width; x++) {
      const nearestColumn = Math.floor(x / scale);
      if (!usable(nearestRow, nearestColumn)) continue;
      let value = values[nearestRow][nearestColumn] as number;
      if (mode === "weather") {
        const fractionalColumn = (x + 0.5) / scale - 0.5;
        const col0 = Math.max(0, Math.min(columns - 1, Math.floor(fractionalColumn)));
        const col1 = Math.max(0, Math.min(columns - 1, col0 + 1));
        const colFraction = Math.max(0, Math.min(1, fractionalColumn - col0));
        if (usable(row0, col0) && usable(row0, col1) && usable(row1, col0) && usable(row1, col1)) {
          const north = (values[row0][col0] as number) * (1 - colFraction) + (values[row0][col1] as number) * colFraction;
          const south = (values[row1][col0] as number) * (1 - colFraction) + (values[row1][col1] as number) * colFraction;
          value = north * (1 - rowFraction) + south * rowFraction;
        }
      }
      const color = mode === "grid" && (palette === "rainfall" || palette === "probability")
        ? rgb(palette === "rainfall" ? rainfallColor(value) : probabilityColor(value))
        : smoothColor(value, palette);
      const offset = (y * width + x) * 4;
      data[offset] = color[0]; data[offset + 1] = color[1]; data[offset + 2] = color[2]; data[offset + 3] = 255;
    }
  }
  const result = { width, height, data };
  byKey.set(key, result);
  return result;
}

export function gridFeatures(grid: Grid, values: (number | null)[][], mask: boolean[][], palette: Palette): FeatureCollection<Polygon> {
  const [rows, columns] = grid.shape;
  if (values.length !== rows || mask.length !== rows || grid.latitude_centers.length !== rows || grid.longitude_centers.length !== columns) {
    throw new Error("Grid dimensions do not match the frozen science contract");
  }
  const half = grid.cell_size_degrees / 2;
  const features: FeatureCollection<Polygon>["features"] = [];
  for (let row = 0; row < rows; row++) {
    if (values[row].length !== columns || mask[row].length !== columns) throw new Error("Grid row dimensions are invalid");
    const latitude = grid.latitude_centers[row];
    for (let column = 0; column < columns; column++) {
      const value = values[row][column];
      if (!mask[row][column] || value == null || !Number.isFinite(value)) continue;
      const longitude = grid.longitude_centers[column];
      const west = longitude - half, east = longitude + half, south = latitude - half, north = latitude + half;
      features.push({
        type: "Feature", id: row * columns + column,
        properties: { row, column, value, color: palette === "rainfall" ? rainfallColor(value) : palette === "probability" ? probabilityColor(value) : `rgb(${smoothColor(value, palette).join(",")})` },
        geometry: { type: "Polygon", coordinates: [[[west, south], [east, south], [east, north], [west, north], [west, south]]] },
      });
    }
  }
  return { type: "FeatureCollection", features };
}
