"use client";

import { useEffect, useRef } from "react";
import { DURATION, countUpText, decimalsOf, shouldAnimate } from "@/lib/motion";

/**
 * A number that counts up once, when it first scrolls into view, and ends on exactly the text it was given.
 *
 * The server and the first client render both contain the final text, so there is no mismatch, no layout shift and nothing wrong for a reader without scripts. The animation then rewrites the text
 * from zero toward the target and restores the exact string at the end. It is skipped (the final text simply stays) for visitors who ask for reduced motion and for automated browsers.
 */
export function CountUp({ value, suffix = "", prefix = "", className }: { value: number | string; suffix?: string; prefix?: string; className?: string }) {
  const element = useRef<HTMLSpanElement>(null);
  const text = typeof value === "number" ? String(value) : value;
  const target = Number(text);
  const finite = Number.isFinite(target);
  useEffect(() => {
    const node = element.current;
    if (!node || !finite || !shouldAnimate() || typeof IntersectionObserver === "undefined") return;
    const decimals = decimalsOf(text);
    let frame = 0;
    const observer = new IntersectionObserver((entries) => {
      if (!entries.some((entry) => entry.isIntersecting)) return;
      observer.disconnect();
      const start = performance.now();
      const tick = (now: number) => {
        const progress = (now - start) / DURATION.count;
        node.textContent = `${prefix}${countUpText(target, decimals, progress)}${suffix}`;
        if (progress < 1) frame = requestAnimationFrame(tick);
      };
      frame = requestAnimationFrame(tick);
    }, { threshold: 0.4 });
    observer.observe(node);
    return () => { observer.disconnect(); cancelAnimationFrame(frame); node.textContent = `${prefix}${text}${suffix}`; };
  }, [finite, prefix, suffix, target, text]);
  return <span ref={element} className={className} data-countup="true">{prefix}{text}{suffix}</span>;
}
