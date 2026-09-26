"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { GeographicStyle } from "@/lib/maps/basemap";

export type DisplayMode = "weather" | "grid";
type Settings = {
  geographicStyle: GeographicStyle;
  setGeographicStyle: (style: GeographicStyle) => void;
  displayMode: DisplayMode;
  setDisplayMode: (mode: DisplayMode) => void;
  opacity: number;
  setOpacity: (value: number) => void;
  boundaries: boolean;
  setBoundaries: (value: boolean) => void;
};

const Context = createContext<Settings | null>(null);

export function MapSettingsProvider({ children }: { children: React.ReactNode }) {
  const [geographicStyle, setGeographicStyle] = useState<GeographicStyle>("dark");
  const [manualStyle, setManualStyle] = useState(false);
  const [displayMode, setDisplayMode] = useState<DisplayMode>("weather");
  const [opacity, setOpacity] = useState(0.78);
  const [boundaries, setBoundaries] = useState(true);
  useEffect(() => {
    if (manualStyle) return;
    const root = document.documentElement;
    const align = () => setGeographicStyle(root.classList.contains("dark") ? "dark" : "light");
    align();
    const observer = new MutationObserver(align);
    observer.observe(root, { attributes: true, attributeFilter: ["class"] });
    return () => observer.disconnect();
  }, [manualStyle]);
  const value = useMemo<Settings>(() => ({
    geographicStyle,
    setGeographicStyle: (style) => { setManualStyle(true); setGeographicStyle(style); },
    displayMode, setDisplayMode, opacity, setOpacity: (next) => setOpacity(Math.max(0.2, Math.min(1, next))),
    boundaries, setBoundaries,
  }), [geographicStyle, displayMode, opacity, boundaries]);
  return <Context.Provider value={value}>{children}</Context.Provider>;
}

export function useMapSettings(): Settings {
  const value = useContext(Context);
  if (!value) throw new Error("MapSettingsProvider is missing");
  return value;
}
