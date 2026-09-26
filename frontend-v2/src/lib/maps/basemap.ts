import type { FeatureCollection } from "geojson";
import type { StyleSpecification } from "maplibre-gl";

export type GeographicStyle = "dark" | "light";
export type BasemapState = "online" | "offline" | "loading";

const DEFAULT_STYLES: Record<GeographicStyle, string> = {
  dark: "https://tiles.openfreemap.org/styles/dark",
  light: "https://tiles.openfreemap.org/styles/positron",
};

const stylePromises = new Map<string, Promise<StyleSpecification>>();

export function geographicStyleUrl(style: GeographicStyle): string {
  const override = style === "dark" ? process.env.NEXT_PUBLIC_OPENFREEMAP_DARK_STYLE : process.env.NEXT_PUBLIC_OPENFREEMAP_LIGHT_STYLE;
  return override || DEFAULT_STYLES[style];
}

export async function onlineStyle(style: GeographicStyle): Promise<StyleSpecification> {
  const url = geographicStyleUrl(style);
  let pending = stylePromises.get(url);
  if (!pending) {
    pending = fetch(url, { signal: AbortSignal.timeout(6500) }).then(async (response) => {
      if (!response.ok) throw new Error(`Basemap style unavailable (${response.status})`);
      const candidate: unknown = await response.json();
      if (!candidate || typeof candidate !== "object" || !("version" in candidate) || candidate.version !== 8 || !("layers" in candidate) || !Array.isArray(candidate.layers)) {
        throw new Error("Basemap style is invalid");
      }
      return candidate as StyleSpecification;
    }).catch((error) => { stylePromises.delete(url); throw error; });
    stylePromises.set(url, pending);
  }
  // MapLibre may normalize a supplied style. Every map receives its own copy.
  return structuredClone(await pending);
}

export function offlineStyle(style: GeographicStyle, geometry?: FeatureCollection): StyleSpecification {
  const dark = style === "dark";
  return {
    version: 8,
    sources: {
      "offline-districts": { type: "geojson", data: geometry ?? { type: "FeatureCollection", features: [] } },
    },
    layers: [
      { id: "offline-ocean", type: "background", paint: { "background-color": dark ? "#0b1a25" : "#d9e8ee" } },
      { id: "offline-land", type: "fill", source: "offline-districts", paint: { "fill-color": dark ? "#1c3340" : "#e4e9df", "fill-opacity": 1 } },
      { id: "offline-coast-and-districts", type: "line", source: "offline-districts", paint: { "line-color": dark ? "#8da7ad" : "#657f87", "line-opacity": 0.55, "line-width": 0.75 } },
    ],
  };
}

export function firstLabelLayer(style: StyleSpecification): string | undefined {
  return style.layers.find((layer) => layer.type === "symbol")?.id;
}
