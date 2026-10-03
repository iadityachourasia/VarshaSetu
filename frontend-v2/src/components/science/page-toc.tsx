"use client";

import { useEffect, useState } from "react";

/** A section counts as "being read" once its top has passed this line (just under the sticky header and the contents bar). */
const READING_LINE = 150;

/**
 * In-page navigation for the long evidence pages; every target is an element with the matching id.
 * The link of the section being read is marked (`aria-current="location"`) as the page scrolls. Without scripts it is the same list of anchors.
 */
export function PageToc({ items }: { items: { id: string; label: string }[] }) {
  const [current, setCurrent] = useState<string | null>(null);
  useEffect(() => {
    let frame = 0;
    const update = () => {
      frame = 0;
      let active: string | null = null;
      for (const item of items) {
        const node = document.getElementById(item.id);
        if (node && node.getBoundingClientRect().top <= READING_LINE) active = item.id;
      }
      setCurrent(active);
    };
    const schedule = () => { if (!frame) frame = requestAnimationFrame(update); };
    update();
    window.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule);
    return () => { window.removeEventListener("scroll", schedule); window.removeEventListener("resize", schedule); cancelAnimationFrame(frame); };
  }, [items]);
  return <nav className="page-toc" aria-label="On this page" data-testid="page-toc"><span className="page-toc-label">On this page</span>{items.map((item) => <a key={item.id} href={`#${item.id}`} aria-current={current === item.id ? "location" : undefined}>{item.label}</a>)}</nav>;
}
