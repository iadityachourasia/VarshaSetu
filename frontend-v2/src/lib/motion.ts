// Small, framework-free helpers for the micro-interactions. Nothing here animates a scientific value in a way that could be mistaken for a measurement: a counted number always
// ends on its exact, formatted value and is never shown above it, and every animation has a no-motion path.

/** Duration tokens in milliseconds; the same values exist as CSS custom properties (--dur-*) so script and stylesheet agree. */
export const DURATION = { fast: 120, base: 200, slow: 320, count: 900 } as const;

export function prefersReducedMotion(): boolean {
  return typeof window !== "undefined" && typeof window.matchMedia === "function" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/** Automated browsers (the end-to-end suite) read the final value at once; animations there would only make text assertions race the clock. */
export function isAutomated(): boolean {
  return typeof navigator !== "undefined" && navigator.webdriver === true;
}

/** The end-to-end suite sets this before the page loads to exercise the animated path; nothing else does. */
function motionForced(): boolean {
  return typeof window !== "undefined" && (window as unknown as { __VARSHASETU_FORCE_MOTION__?: boolean }).__VARSHASETU_FORCE_MOTION__ === true;
}

export function shouldAnimate(): boolean {
  return !prefersReducedMotion() && (!isAutomated() || motionForced());
}

/** Ease-out cubic: fast start, gentle landing. Defined on [0, 1] and clamped outside it. */
export function easeOut(progress: number): number {
  const p = Math.min(1, Math.max(0, progress));
  return 1 - Math.pow(1 - p, 3);
}

/** Number of decimal places a value is written with ("9.73" has 2, "12" has 0). */
export function decimalsOf(text: string): number {
  const match = /\.(\d+)/.exec(text);
  return match ? match[1].length : 0;
}

/**
 * The text shown at a point of a count-up toward ``target``. It is the exact ``target`` text at progress 1 (and beyond), and between 0 and the target otherwise,
 * so it can never overshoot the true value.
 */
export function countUpText(target: number, decimals: number, progress: number): string {
  if (progress >= 1) return target.toFixed(decimals);
  return (target * easeOut(progress)).toFixed(decimals);
}
