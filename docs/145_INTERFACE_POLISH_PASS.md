# 145. Interface polish pass

Status: built 4 October 2026. Scope: front end only. No scientific value, API, artifact or protocol changed.

## How it was found

Every route (15) was captured in light, dark and phone layouts from the production build and reviewed page by page. The findings below were fixed; the rest are listed at the end.

## Defects fixed

| Where | Problem | Fix |
|---|---|---|
| Home, hero result card | "mm" wrapped under each value and a stray bar appeared: the count-up added an inner `<span>` and the `.result-pair span` rules styled it too | Rules scoped to direct children (`.result-pair > span`) |
| Regime Intelligence | The "on this page" bar sat above the page title (every other long page puts it under the title) | The bar is passed into the regime view and rendered right after the heading |
| Regime Intelligence | "Case distribution by dominant pseudo-regime" rendered as unstyled stacked text: `.phase5-regime-line` had no CSS | Label, proportional bar and count on one row; on phones the bar moves under the label |
| Regime Intelligence | "Forecast-to-routing pathway" rendered as a plain list: `.phase5-pipeline` had no CSS | Numbered steps joined by arrows (vertical on phones) |
| Regime Intelligence (2023–2025) | `.phase5-regime-layout` had no CSS | Two-column layout on desktop, one column below 900 px |
| Phones, evidence tables | Wide tables were cut off at the card edge | Tables inside evidence cards scroll sideways on narrow screens |

## Visual system

- **Raw vs corrected colour.** Raw GEFS was a dark blue next to a teal correction; the two lines of the home-page charts were hard to tell apart. Raw is now warm (`--chart-raw`, orange) and the correction keeps the brand teal, which also separates them for red–green colour blindness. Model colours elsewhere are unchanged.
- **Cards.** One radius, a soft shadow, a small accent bar on card titles, and a quieter fill for a card inside another card (the district verification panel).
- **Caveat lists.** Lists of limitations were a stack of separately boxed items; they are now one container with bullets (ordered lists keep their numbers). Single caveat paragraphs keep their box.
- **Tables.** Tabular figures so digits align; the row under the pointer is tinted.
- **Filter pills.** Rounded, with a hover state and a firmer selected state.
- **Details.** Selection colour, thin scrollbars, and a default keyboard focus ring for any control that does not define its own.

## Event Casebook (2019)

The 2019 casebook was one 255-row list with no way to narrow it. It now has filters (observed event, lead, case outcome), sorting (date, largest RMSE reduction, most Heavy cells), a live summary (cases shown, cases with lower corrected RMSE, cases with an observed Heavy cell), and richer rows: the case's dominant pseudo-regime, event chips that light up when Heavy or Very Heavy cells were observed, and the RMSE change coloured and scaled. Every value is read from the frozen case records; "lower corrected RMSE" means only that the case's corrected RMSE is below its Raw RMSE.

## Not changed (noted for later)

- On phones, the first forest plot of a group (the one with row labels) is drawn at a fixed width and scales down to small text.
- The live-cycle field preview is a low-resolution raster by design (the stored field is coarse).

## Checks

Type-check and lint clean; Vitest 209 passed; Playwright 160 passed, 5 skipped (the hidden compliance page). Before/after captures were reviewed for home, regimes, verification, casebook and the phone layout.
