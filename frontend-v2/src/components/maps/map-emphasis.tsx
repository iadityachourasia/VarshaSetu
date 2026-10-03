"use client";

import { createContext, useContext, useMemo, useState } from "react";
import type { Emphasis } from "@/lib/maps/emphasis";

type Value = { emphasis: Emphasis | null; setEmphasis: (next: Emphasis | null) => void };
const Context = createContext<Value>({ emphasis: null, setEmphasis: () => undefined });

/** The legend class currently under the pointer or keyboard focus. Shared so that every map on the page, not only the one beside the legend, dims the same cells. */
export function MapEmphasisProvider({ children }: { children: React.ReactNode }) {
  const [emphasis, setEmphasis] = useState<Emphasis | null>(null);
  const value = useMemo(() => ({ emphasis, setEmphasis }), [emphasis]);
  return <Context.Provider value={value}>{children}</Context.Provider>;
}

export function useMapEmphasis(): Value {
  return useContext(Context);
}
