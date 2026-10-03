"use client";

import { useEffect } from "react";
import { shouldAnimate } from "@/lib/motion";

/**
 * Publishes whether decorative motion is allowed as `data-motion="on" | "off"` on the document element, so stylesheet-driven entrances can be switched off in one place
 * (reduced-motion preference, automated browsers). It follows a change of the preference while the page is open.
 */
export function MotionRoot() {
  useEffect(() => {
    const apply = () => { document.documentElement.dataset.motion = shouldAnimate() ? "on" : "off"; };
    apply();
    const query = typeof window.matchMedia === "function" ? window.matchMedia("(prefers-reduced-motion: reduce)") : null;
    query?.addEventListener("change", apply);
    return () => query?.removeEventListener("change", apply);
  }, []);
  return null;
}
