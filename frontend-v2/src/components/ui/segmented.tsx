"use client";

import { useLayoutEffect, useRef, useState } from "react";
import { shouldAnimate } from "@/lib/motion";

export type SegmentedOption<T extends string> = { value: T; label: React.ReactNode };

/**
 * A group of toggle buttons with one selected value and a highlight that slides to it.
 *
 * It keeps the plain structure the stylesheet and the tests already know (`.segmented`, `button.selected`, `aria-pressed`, a labelled `role="group"`), so without scripts, or before the highlight has been measured,
 * the selected button simply paints its own background. Once measured, the highlight is a separate element and the selected button turns transparent. Visitors who ask for reduced motion get the highlight
 * without the slide.
 */
export function Segmented<T extends string>({ value, options, onChange, label, className = "" }: {
  value: T; options: ReadonlyArray<SegmentedOption<T>>; onChange: (next: T) => void; label: string; className?: string;
}) {
  const group = useRef<HTMLDivElement>(null);
  const [box, setBox] = useState<{ left: number; width: number } | null>(null);
  const [animate, setAnimate] = useState(false);
  useLayoutEffect(() => {
    const root = group.current;
    if (!root) return;
    const measure = () => {
      const selected = root.querySelector<HTMLElement>("button.selected");
      if (!selected) return setBox(null);
      setBox({ left: selected.offsetLeft, width: selected.offsetWidth });
    };
    measure();
    const observer = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(measure);
    observer?.observe(root);
    // The first measurement must not slide in from the left edge; later changes do.
    const frame = requestAnimationFrame(() => setAnimate(shouldAnimate()));
    return () => { observer?.disconnect(); cancelAnimationFrame(frame); };
  }, [value, options.length]);
  return <div ref={group} className={`segmented${box ? " segmented-ready" : ""}${animate ? " segmented-animated" : ""} ${className}`.trim()} role="group" aria-label={label}>
    {box ? <span className="segmented-thumb" aria-hidden="true" style={{ transform: `translateX(${box.left}px)`, width: box.width }} /> : null}
    {options.map((option) => <button key={option.value} type="button" className={value === option.value ? "selected" : ""} aria-pressed={value === option.value} onClick={() => onChange(option.value)}>{option.label}</button>)}
  </div>;
}
