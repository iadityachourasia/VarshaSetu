# Phase 3A Design System

VarshaSetu uses a meteorological operations visual language, with light mode
on a first visit and a user-selectable dark mode:
near-black navy ground, tiered slate surfaces, thin disciplined rules,
controlled teal accents, and direct scientific typography. This is an
operational workspace, not a generic landing page or trading terminal.
The light mode reuses semantic tokens rather than duplicate component styles.
An explicit theme choice persists locally; system color preference does not
override the first-visit light default.

`frontend-v2/src/app/globals.css` is the executable token source. Core
semantic colors are `--background`, `--surface-raised`,
`--surface-recessed`, `--foreground`, `--text-subtle`, `--line`, and
`--teal`. Scientific series are stable across routes: `--raw` (blue),
`--corrected` (teal), `--observed` (violet). Heavy-event emphasis is amber;
very-heavy is rose. Palettes do not depend on red/green alone. The shared
rainfall bins explicitly cross 64.5 and 115.6 mm/24h; the probability
palette is separate and labeled 0–100%.

Use the local system variable sans stack beginning with Segoe UI Variable
and a code/metadata stack beginning with Cascadia Code. Self-contained
system fonts keep production builds reproducible when Google Fonts is
unreachable. Major headings use tight tracking and compact vertical rhythm;
metadata, timestamps and hashes use the mono stack. The design uses 4–10px
radii, restrained elevation, clear focus rings and `prefers-reduced-motion`.

Core reusable primitives are `PageHeading`, `SectionHeading`, `Metric`,
`PrototypeNote`, `ErrorState`, `LoadingState`, `CaseSelector`, `RegimeBars`,
`GridMap`, `RainLegend`, and `ProbabilityLegend`. Shadcn/Base UI supplies
accessible low-level buttons, Sheet and Tooltip. Maps are the visual anchor
of Forecast Explorer, Extreme Rain and District Intelligence; tables remain
semantic and sortable. Undefined values render as “Undefined” or
“Unavailable”, never as an invented zero.

All scientific labels explicitly say “historical prototype” where a viewer
might mistake a case for live weather. A prominent 9.73% RMSE result is
paired with the limitation that Raw GEFS retains stronger deterministic
extreme-event skill. No animated or decorative content represents data.

## Overview visual treatment (2026-09-28)

The Overview uses the supplied dark/light AVIF artwork as decorative imagery
for its hero and three evidence links. CSS selects the matching asset for the saved theme,
while a tonal overlay preserves text contrast. The light hero veil is thinner
over the artwork to reduce the white haze, while the copy side retains a
slightly stronger wash for readability, including on small screens. The hero
title uses larger type with restrained letter spacing. The shared
sidebar and header
use stronger active navigation and control hierarchy. On desktop the sidebar
starts as a 64px icon rail. Moving a mouse anywhere into the rail expands its
existing labeled navigation; leaving the sidebar contracts it. The logo-position
control remains available for keyboard and touch input. Hovering or focusing
that control reveals the panel icon. The rail and labels
reveal as one bounded transition; mobile
keeps its closed drawer, which slides in on opening. Both paths retain keyboard
access and honor reduced motion. The sidebar ends with
a compact blue glass link to the historical casebook, with accurate 2019 and
2025 case-year copy, a clock icon, and a visible keyboard focus state. The
card uses a solid theme-matched fill when transparency is reduced. Scientific
series still use the established
Raw and corrected color roles.

The supplied VS marks appear in the shared sidebar, mobile header and drawer,
and presentation identity. The white-backed artwork is used in light mode.
The dark-mode mark is a transparent-background extraction of the supplied
cyan-backed source, so the letterform sits directly on the navy surface.
Both are decorative beside the accessible VarshaSetu name.

The Regime Intelligence development state uses a full-height, type-led layout
in both themes. It carries the exact feature availability copy and a route
back to the overview without presenting unavailable scientific data as a chart
or metric.

The compact inset shared top bar places the supplied VS logo, VarshaSetu wordmark,
and scientific workspace context on one row. The wordmark returns to
the overview. Its left and right borders use the same responsive content gutter
as the hero, benchmarks, and evidence sections. Its experiment selection
and utility controls remain grouped to the right, with Present VarshaSetu as
the single filled action. The separate Presentation View control and shortcut
have been removed. The mobile top row carries the VS mark and
wordmark. The 12-scene presentation mounts at the document root so its modal
covers the full viewport even though the glass header uses backdrop blur;
opening it locks background scrolling and makes the workspace inert, while
closing restores focus to the trigger.

The desktop wordmark, slash, and workspace descriptor share a text baseline,
while the mark stays vertically centered. “Setu” uses `#54EDF2` in dark mode;
light mode uses a darker teal to keep the wordmark readable on its pale surface.
On mobile the brand mark, wordmark, slash, and workspace label share a centerline;
the light hero copy veil fades vertically into the artwork below its actions.

The generated browser and install icons live in `frontend-v2/public`. Root
layout metadata declares the SVG, PNG, ICO, Apple touch icon, web-app title,
and manifest once for every route. The older App Router favicon file was
removed to avoid a duplicate icon link.

The paired 2019 and 2025 panels retain separate source identities and a
visible non-pooling caveat. Each panel leads with its sourced aggregate RMSE
reduction as the largest figure, followed by aligned raw and corrected RMSE
values and case evidence. The shared caveat strip immediately below the panels
keeps the 2025 Raw-better extreme FSS limitation visible without repeating it
inside the 2025 card. Both cards use tighter bottom padding. Charts show actual unsmoothed
per-case RMSE ordered by forecast initialization; connecting segments are
only visual joins between distinct cases, not a continuous rainfall trend.
If a complete eligible paired series is unavailable, the panel shows
sourced aggregate comparison bars and labels the case series unavailable.

Overview cards and the shared shell use restrained translucent surfaces,
fine highlight borders, and moderate backdrop blur. Solid semantic
surfaces are the fallback when blur is unsupported or the viewer prefers
reduced transparency. All detailed scientific map and table panels retain
their established flat data treatment. At narrow widths the hero is
compressed so the 2019 result appears sooner; charts scroll within their
own panels instead of causing page overflow. Text over artwork uses a
strong veil, and the compact image-backed links use a clear icon, text block,
and circular arrow. The homepage omits explanatory image and reliability
footnotes to keep the overview concise; scientific scope remains in the
benchmark labels, caveats, and linked verification views.

The hero uses a wide primary forecast link and a bordered validation link.
A slim amber verification link states the non-pooled GEFS lineages and
Raw-better 2025 extreme FSS caveat. Six compact 2025 evidence cards show
continuous RMSE, spatial FSS, Heavy and Very Heavy BSS together with high
FAR, regime comparison, and frozen data provenance. At constrained widths
the cards reflow to preserve readable labels rather than shrinking them.

## 2019 overview outage state

The overview's 2019 benchmark may show a small “API unreachable · verified
frozen 2019 snapshot” label when the scientific API cannot be reached. The
snapshot is the same held-out result and per-case series, with its own source
identity; it is not current forecast data. Integrity and contract failures
retain the unavailable state.
