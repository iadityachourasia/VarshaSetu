# Phase 3A Design System

VarshaSetu uses a dark-first meteorological operations visual language:
near-black navy ground, tiered slate surfaces, thin disciplined rules,
controlled teal accents, and direct scientific typography. This is an
operational workspace, not a generic landing page or trading terminal.
The light mode reuses semantic tokens rather than duplicate component styles.

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
