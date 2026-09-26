"use client";

import { Maximize2, Minus, Plus, RotateCcw } from "lucide-react";
import { useMapSettings } from "./map-settings";

export function MapControls({ onReset, onZoom, onFullscreen, district = false }: {
  onReset: () => void;
  onZoom: (delta: number) => void;
  onFullscreen?: () => void;
  district?: boolean;
}) {
  const settings = useMapSettings();
  return <div className="map-toolbar" aria-label="Map display controls">
    <label>Geography <select aria-label="Geographic map style" value={settings.geographicStyle} onChange={(event) => settings.setGeographicStyle(event.target.value as "dark" | "light")}><option value="dark">Dark Geographic</option><option value="light">Light Geographic</option></select></label>
    {!district ? <label>Display <select aria-label="Scientific display mode" value={settings.displayMode} onChange={(event) => settings.setDisplayMode(event.target.value as "weather" | "grid")}><option value="weather">Weather Visualization</option><option value="grid">Scientific Grid</option></select></label> : null}
    {!district ? <label className="opacity-control">Overlay <input aria-label="Scientific overlay opacity" type="range" min="20" max="100" step="5" value={Math.round(settings.opacity * 100)} onChange={(event) => settings.setOpacity(Number(event.target.value) / 100)} /><output>{Math.round(settings.opacity * 100)}%</output></label> : null}
    <label className="map-check"><input type="checkbox" checked={settings.boundaries} onChange={(event) => settings.setBoundaries(event.target.checked)} /> Boundaries</label>
    <div className="map-toolbar-actions"><button type="button" aria-label="Zoom in" title="Zoom in" onClick={() => onZoom(1)}><Plus size={15} /></button><button type="button" aria-label="Zoom out" title="Zoom out" onClick={() => onZoom(-1)}><Minus size={15} /></button><button type="button" aria-label="Reset map extent" title="Reset map extent" onClick={onReset}><RotateCcw size={15} /></button>{onFullscreen ? <button type="button" aria-label="Toggle map fullscreen" title="Toggle map fullscreen" onClick={onFullscreen}><Maximize2 size={15} /></button> : null}</div>
  </div>;
}
