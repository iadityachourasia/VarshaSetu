"use client";

import { useState } from "react";
import type { BasemapState } from "@/lib/maps/basemap";

/**
 * Map data credits, collapsed to a small "i" so they do not cover the map. The full credits open on hover, on keyboard focus or on a click/tap
 * (which keeps them open until the next click), as the OpenStreetMap and ODbL attribution terms allow for interactive maps.
 */
export function MapAttribution({ status }: { status: BasemapState }) {
  const [open, setOpen] = useState(false);
  return <div className={`map-attribution${open ? " is-open" : ""}`}>
    <button type="button" className="map-attribution-toggle" aria-expanded={open} aria-label={open ? "Hide map data credits" : "Show map data credits"} title="Map data credits" onClick={() => setOpen((value) => !value)}>i</button>
    <span className="map-attribution-text">
      {status === "offline" ? <>Offline district geography: </> : <><a href="https://openfreemap.org/" target="_blank" rel="noopener noreferrer">OpenFreeMap</a> © <a href="https://openmaptiles.org/" target="_blank" rel="noopener noreferrer">OpenMapTiles</a> · Data © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap contributors</a> · </>}
      Districts: <a href="https://www.geoboundaries.org/" target="_blank" rel="noopener noreferrer">geoBoundaries</a>, <a href="https://opendatacommons.org/licenses/odbl/1-0/" target="_blank" rel="noopener noreferrer">ODbL 1.0</a>
      {status === "offline" ? " · No online street or terrain detail" : null}
    </span>
  </div>;
}
