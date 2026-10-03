# 144. Interface motion and map interactions

Status: built 4 October 2026. Scope: front end only. No scientific value, API, artifact or protocol changed.

## Principle

Motion is used to show where something went or what a control refers to, never to dress up a number. Every item below has a no-motion path: visitors who ask the operating system for reduced motion get the same state changes without the movement, and automated browsers (`navigator.webdriver`) skip decorative motion unless a test turns it on with `window.__VARSHASETU_FORCE_MOTION__`. `src/lib/motion.ts` holds the shared helpers and the duration tokens (the same values exist as CSS custom properties `--dur-*`).

## What was added

| Item | Where | Behaviour | Reduced motion |
|---|---|---|---|
| Sliding segmented control | `components/ui/segmented.tsx`; used for threshold, output, classifier layer and corrected-model choices | A highlight slides to the selected button. Same markup the tests knew (`.segmented`, `button.selected`, `aria-pressed`, labelled group); before it is measured, the selected button paints its own background. | highlight moves without sliding |
| Exact count-up | `components/ui/count-up.tsx`; the two homepage headline blocks (percentage and the two RMSE values) | Counts once when scrolled into view. Server and first client render already contain the final text; the last frame writes the exact string; the value never exceeds the target on the way (unit-tested). | final text only |
| Copy-hash chip and toast | `components/ui/hash-chip.tsx`, `toast.tsx`; every printed digest | Click copies the full SHA-256 and confirms in a polite live region. If the browser blocks the clipboard it says so instead of failing silently. | toast appears without its entrance |
| Download confirmation | `components/ui/download-link.tsx`; report links | Still a real `<a download>`; also confirms that the download started. | no entrance |
| Scroll-spy | `components/science/page-toc.tsx` | The section being read is marked with `aria-current="location"`. | no transition |
| Forest plot | `components/science/forest-plot.tsx` | Intervals draw in once; the row under the pointer is emphasised; each row has a native tooltip with its value, interval and whether it excludes zero. | no animation |
| Content fade-in | stylesheet, `[data-motion="on"] .page-content > *` | What replaces a loading state fades in (opacity only, no layout shift). | none |
| District table ↔ map | `district-map.tsx`, both district workspaces | Pointing at a row outlines its polygon; pointing at a polygon marks its row. | no transition |

### Map interactions

| Item | Behaviour |
|---|---|
| Legend class emphasis | Hovering or focusing a legend class (each is a button) dims every map cell outside it, on every map of the page that draws the same kind of quantity. Alpha only; colours and values are untouched (unit-tested). |
| Raster crossfade | When the data drawn on a persistent map changes (corrected-model switch, threshold switch, display mode), the old picture fades out while the new one fades in. |
| Selected-cell ring | A ring leaves the cell that was just chosen. Not for the first selection of a page load. |
| Shared pointer | On the three Forecast maps, the cell under the pointer on one map is outlined on the others. |

## What is deliberately not done

- **A new case does not crossfade.** Choosing another historical case replaces the maps with their loading state (the maps are rebuilt), then the content fades in. Crossfading between cases would mean showing the previous case's field under the new case's labels while the new one loads, which is a risk to the honesty of what is on screen and was not accepted for the sake of polish.
- Swipe-to-compare and a case scrubber are not part of this batch.
- No animated number is ever a scientific measurement in motion: the count-up ends on the written value and is limited to two headline blocks.

## Checks

- `src/lib/motion.test.ts` (count-up never overshoots and lands exactly), `src/lib/maps/emphasis.test.ts` (legend classes partition the axis; emphasis changes alpha only; cache not disturbed).
- `frontend-v2/tests/e2e/micro-interactions.spec.ts`: each item on the animated path and under `prefers-reduced-motion: reduce`.
