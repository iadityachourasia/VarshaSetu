// A few map specs need the public OpenFreeMap basemap (tiles and glyphs). They are skipped, with a stated reason, when that
// host is unreachable (offline development, CI sandboxes) so a network outage is never reported as a product failure.
export async function basemapReachable(): Promise<boolean> {
  try {
    const response = await fetch(process.env.BASEMAP_PROBE_URL ?? "https://tiles.openfreemap.org/planet", { signal: AbortSignal.timeout(6000) });
    return response.status < 500;
  } catch {
    return false;
  }
}

export const BASEMAP_SKIP_REASON = "the public OpenFreeMap basemap host is unreachable from this machine";
