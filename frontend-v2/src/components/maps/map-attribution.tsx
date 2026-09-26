import type { BasemapState } from "@/lib/maps/basemap";

export function MapAttribution({ status }: { status: BasemapState }) {
  return <span className="map-attribution">
    {status === "offline" ? <>Offline district geography: </> : <><a href="https://openfreemap.org/" target="_blank" rel="noopener noreferrer">OpenFreeMap</a> © <a href="https://openmaptiles.org/" target="_blank" rel="noopener noreferrer">OpenMapTiles</a> · Data © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap contributors</a> · </>}
    Districts: <a href="https://www.geoboundaries.org/" target="_blank" rel="noopener noreferrer">geoBoundaries</a>, <a href="https://opendatacommons.org/licenses/odbl/1-0/" target="_blank" rel="noopener noreferrer">ODbL 1.0</a>
    {status === "offline" ? " · No online street or terrain detail" : null}
  </span>;
}
