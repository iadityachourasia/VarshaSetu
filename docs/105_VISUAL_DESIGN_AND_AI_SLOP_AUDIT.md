# VarshaSetu Visual Design and “AI-Slop” Audit

**Date:** 2026-09-28 IST  
**Scope:** Read-only review of local `frontend-v2/` at `4a88855` and the deployed `https://varshasetu.vercel.app/`. No frontend or scientific files were edited.  
**Evidence:** Real Chromium, 66 settled route/theme/viewport captures, 11 interaction/detail captures, live computed styles, local CSS/components, and the Impeccable detector. Screenshots are ignored artifacts in `test-results/design-audit/`. All 66 primary captures returned HTTP 200 and had no settled document-level horizontal overflow. The review is a design assessment, **not** a revalidation of scientific values or provenance.

## Executive verdict

The interface is functionally substantial and scientifically more honest than a generic weather dashboard: it distinguishes the 2019 reforecast and 2025 historical operational tracks, marks the prototype status, shows raw/corrected/observed maps, and includes caveats alongside metrics. Its *visual grammar*, however, reads like a polished admin template applied repeatedly to scientific material. Nearly every route begins with the same large title/subtitle, outlined prototype note, teal-edged context strip, and rounded bordered panel. Dark navy plus mint/teal, monospaced uppercase labels, Lucide navigation icons, and boxed metrics produce a recognizable developer/AI SaaS aesthetic. The actual meteorological instruments are too often pushed below generic controls and status furniture.

One issue is a confirmed functional defect, not a taste judgment: **Story Mode does not occupy the viewport**. On the live 1440px page its `.story-overlay` measures `x=248, y=0, width=1192, height=63`, despite `position: fixed; inset: 0`. It is mounted inside the sticky `.global-header`, whose `backdrop-filter` creates the containing block; only its 63px top segment overlays the page. See `frontend-v2/src/components/layout/app-shell.tsx:95,174`, `frontend-v2/src/app/globals.css:402,460`, and `dark-1440-story-mode.png`. This merits P0 because the named presentation feature is visibly unusable.

## Method and limits

- Local source was inspected for real declarations rather than treating `DESIGN.md` as the implementation. `layout.tsx` declares local Inter/JetBrains Mono font assets, but live computed `--font-geist-sans` is `"Segoe UI Variable", "Segoe UI", "Inter", Arial`, and `--font-geist-mono` is `"Cascadia Code", Consolas, "Liberation Mono", monospace`; the four declared `@font-face` entries were **unloaded** in the live probe. This is a verified effective-style finding, not an inference from a screenshot. See `frontend-v2/src/app/layout.tsx:7-8`, `globals.css:43-44,51-52`, `test-results/design-audit/probes.json`.
- The initial `domcontentloaded` pass caught loading skeletons and transient chart overflow. Captures were repeated after map/chart readiness and settling. The final 66-screen matrix has zero document overflow. A 670px Verification table intentionally scrolls inside `.comparison-table-wrap` on 390px; its off-viewport cells are not page overflow.
- The first screenshot captures the viewport, not every below-fold element. Additional scrolled captures cover charts, matrix, lineage, and analysis panels. Render cold starts and map geography loading can change transient states; the report judges settled screenshots unless explicitly marked.
- The Impeccable detector found no component-markup hits and six CSS warnings: five left-accent borders at `globals.css:276,330,343,369,438`, plus width animation at `:406`. The border warnings corroborate the repeated “status strip” visual motif; they do not prove every accent line is wrong. The unavailable `21st` CLI could not run its deterministic review. [Vercel's Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md) were used as a secondary interaction/accessibility checklist, not as a substitute for visual judgment.

## Current design language

The current language is a dark/light administrative workspace with a 248px persistent sidebar, 64px sticky desktop header, 28px page titles, 20–24px panel padding, 6/8/12px declared radius tokens, muted blue-gray borders, and a mint/teal active state. Most science pages use 11px microcopy, 12.5px data-table text, monospaced tracked metadata, and a repeatable title → caveat strip → filters → bordered cards sequence. The visual system is internally recognizable but weakly specific to meteorology; another analytics SaaS product could inherit it with a content swap.

## Current color palette

The key effective palette is below; values are CSS tokens in `globals.css:43-167`, not a proposed replacement. “Frequency” is qualitative visual usage: shell/surfaces are constant, model colors appear where a chart or map needs them.

| Role / token | Light | Dark | Actual use and visual reading |
|---|---|---|---|
| `--background` | `#f4f7f8` | `#0a141d` | Every page; dark navy contributes strongly to the familiar AI-dashboard look. |
| `--sidebar` | `#eaf0f2` | `#0d1b25` | Persistent navigation field; restrained but generic admin treatment. |
| `--surface-raised` | `#ffffff` | `#12232e` | Repeated cards/panels; high frequency. |
| `--surface-recessed` | `#edf3f5` | `#0d1c26` | Header, table headings, nested metrics; frequent. |
| `--foreground` | `#14242e` | `#e9f2f2` | Primary text; readable at headline scale. |
| `--text-subtle` | `#4d626d` | `#acc1c7` | Explanations and most 11px labels; overused as a small-text treatment. |
| `--line` | `#cbd8dc` | `#29404b` | Almost every panel; 49 literal `border: 1px solid var(--line)` declarations in the stylesheet. |
| `--teal` / `--primary` | `#006b6d` | `#7bd3c5` | Navigation active, CTAs, results, chart lines, accents; overdominant, especially dark. |
| `--raw` | `#27628a` | `#78b7df` | Raw forecast/model M0; scientific encoding with a stable role. |
| `--corrected` | `#087f81` | `#7bd3c5` | Corrected/M1; merges visually with the general UI accent. |
| `--observed` | `#6d53a2` | `#c1a9f2` | IMD observation; violet is semantically motivated but reinforces the cyan/purple AI palette. |
| `--model-m2/m3/m4` | `#3a6ea5 / #a8632e / #9a4a86` | `#8ab4e0 / #e2a06b / #d99bc7` | Model ladder; distinct but starts to resemble categorical BI-chart color coding. |
| `--amber`, `--danger` | `#855414 / #b84654` | `#f2bd70 / #ef8792` | Caveats and negative states; appropriate meanings, very visible as left-border notes. |
| `--semantic-positive/info` | `#2f7a4f / #2a6fa8` | `#6fcf97 / #7fb8e0` | Status semantics; coexist with model, map, and accent colors. |

The rainfall ramp (`globals.css:247`) spans navy→blue→cyan→mint→amber→red; the probability ramp spans violet→blue→cyan→green→yellow. These gradients are *data encodings*, not decorative hero gradients, and should be evaluated by legend/task. The small Overview hero gradient (`:256`) adds little functional meaning. There is no conspicuous glowing neon treatment; the problem is cumulative sameness of dark navy, teal borders, colored badges, and adjacent scientific palettes. Dark mode feels like a developer analytics product; light mode is cleaner but closer to generic enterprise SaaS.

## Current typography

The intended Inter/JetBrains assets are in `layout.tsx`, yet the live browser used Segoe UI Variable for body and Cascadia/Consolas for mono because `:root` redefines the same font variables (`globals.css:51-52`). Font usage therefore varies by platform; the product's supposed type identity is not reliably delivered. The body face is legible, but it has little meteorological or institutional character. The mono stack is used for data context, caps labels, source IDs, and claims; the frequency makes the interface feel like a code tool.

The type tokens are 11 / 12.5 / 14 / 15 / 17 / 20 / 26 / 32px (`globals.css:53-60`), but 84 literal `font-size: 11px` declarations remain. This is a pervasive minimum, not a deliberately rare micro label. Examples include Casebook row metadata, Forecast INIT/LEAD/IMD DATE/ROLE, chart captions, table headers, verification notes, and sidebar group labels. Heading sizes/weights vary from the 65px Overview brand to 28px page titles, 17px section titles, 15px shared headings, and 11px uppercase eyebrow labels. `650`, `620`, `670`, `580` fractional font weights and negative tracking on major metrics create a synthetic “precision-polished” feel. Tabular numerals and right-aligned table values are strengths; 107px Overview `9.73%` and 44px Verification result overpower uncertainty and sample context.

## Current spacing, density, radius, border, and shadow system

The declared spacing scale is 4/8/12/16/20/24px (`globals.css:61-66`), but page-specific CSS uses 3, 5, 6, 7, 9, 10, 11, 13, 14, 17, 18, 19, 22, 23, 25, 29, 30, 33, 35, 40, 42, and 45px. The scale is aspirational rather than governing. Effective desktop sidebar is 248px, header 64px, global select/buttons 34px; main page padding is roughly 28px. Mobile has a two-row 52px app bar plus 52px control strip with 44px targets—an improvement over the former three-row header.

Declared radii are control 6px, surface 12px, theme 6/8/12px. Legacy rules also use 2/3/4/5/7/8/10px and 999px pills. Five main surfaces were grouped under the 12px surface radius and level-one shadow (`globals.css:477`), while many secondary cards retain different corners. Shadows are subtle (`--shadow-1` 0 3px 12px; `--shadow-2` 0 12px 32px), so the app does not look “glowy”; repeated outlines and nested rectangles contribute more to template feeling than elevation. The light theme's white cards and shadows amplify the SaaS-card impression. Borders often encode containment *and* warning *and* decoration, which blurs their meaning.

Density is inconsistent: Casebook's rows spend large vertical area on minimal case metadata, while Forecast compresses five selects, metadata, geography/display controls, map tools, and three map headings above the data. Quality's four large boxed counts create whitespace where a simple attrition table or flow could be denser. On a 900px screen, Forecast's maps begin around 399px, leaving only their upper halves in the initial view. This is an instrument-priority problem, not merely a padding defect.

## Recurring “AI-slop” patterns and component repetition

| Pattern and severity | Where it recurs | Why it feels artificial |
|---|---|---|
| **HIGH — same route grammar** | Forecast, Casebook, Extreme Rain, Ensemble, Regimes, Quality, Audit | Shared `PageHeading` + subtitle + `PrototypeNote` + teal context strip starts unrelated scientific tasks identically. |
| **HIGH — box inside box** | Overview benchmark pair/status grid; Quality funnel inside analysis block; Observations year tiles inside lineage panels; Verification Brier tiles beside chart | Information hierarchy is expressed mainly by adding another border, not by analytical relationship. |
| **HIGH — oversized number/tiny context** | Overview 9.73%, Verification result, Extreme Rain Brier/BSS tiles, Quality counts | Promotional metric-card convention makes the result feel celebrated before the reader sees scope/limitations. |
| **HIGH — 11px uppercase mono furniture** | Sidebar groups, context strips, track/year labels, INIT/LEAD/ROLE, status grid | Gives every page a “machine console” texture without helping scan hierarchy. |
| **MEDIUM — repeated colored left rail** | Context strips, caveats, provenance aside, honesty notes (`globals.css:276,330,343,369,438`) | A common AI dashboard callout pattern becomes the default way to distinguish scientific notes. |
| **MEDIUM — icon with every navigation item** | All 12 sidebar links, mobile drawer, header actions | Lucide is consistent but interchangeable with an admin template; some symbols are generic or metaphorically weak. |
| **MEDIUM — badges/status pills** | Sidebar “Historical prototype,” every `PrototypeNote`, source chips, table “Best 2019 RMSE,” role strips | Multiple enclosures compete with actual metadata. The scientific warning is essential; repeated pill styling is the issue. |
| **MEDIUM — repetitive rounded white/navy surfaces** | Most pages through `.phase5-analysis-block`, `.map-panel`, `.verification-headline`, `.method-intro` | Unrelated content appears as equal-ranking cards. |
| **LOW — decorative gradients/shadows** | Overview hero, shimmer loading blocks, tooltip/drawer elevation | Subtle individually; cumulatively adds off-the-shelf polish rather than domain identity. |

Yes: many pages feel like the same dashboard template with different nouns. The strongest exceptions are the actual triptych maps, the six-season matrix, the model table, and the provenance DAG; these contain task-specific material. Their outer presentation still tends to inherit the same card shell. Shared primitives in `frontend-v2/src/components/science/common.tsx:8-33` explain much of the repetition; the source should keep reusable semantics, but future visual hierarchy needs route-specific information architecture.

## Sidebar and header

**Sidebar.** The 248px width and 42px item targets are usable on laptops; active tint and a 3px teal indicator are clear. Three uppercase group labels plus dividers create an admin rail. The square `V` mark, Lucide icons, and bottom status pill look like a generic shadcn-style navigation system, not a tool built around forecast issue time, geospatial layers, and verification workflows. In rail mode the pictograms have limited domain specificity. The mobile off-canvas drawer is coherent and readable, but repeats the same icon taxonomy. The footer status pill adds one more badge to an already badge-heavy page.

**Header.** The page-independent “VarshaSetu / Scientific workspace” kicker and “Two separate historical GEFS lineages” context are scientifically careful, but the global row packs an experiment select, Reset Demo, Presentation View, Present VarshaSetu, and theme toggle at equal 34px height. A user on Quality or Methodology sees experiment context even when the page is chiefly explanatory. The header feels assembled from utility controls rather than prioritized around the current analysis. Its translucent backdrop (`globals.css:460`) also causes the Story Mode clipping defect. The new mobile two-row top bar is comparatively restrained and has 44px targets; it is one of the cleaner parts of the shell.

## Page-by-page personality audit

### Overview — deep review

The first viewport communicates “AI product result” before “scientific investigation”: a large VarshaSetu wordmark, broad tagline, primary teal CTA, and giant `9.73%` occupy a split hero (`globals.css:256-264`). The 2019 provenance is present but rendered as 11px eyebrow text, while the percentage is roughly 107px. This disproportion makes the result feel like a sales claim even though its caveat is accurate. Two near-identical 2019/2025 benchmark cards then repeat negative RMSE percentages, followed by six boxed status facts. The 2025 limitation and non-pooled-track note are visually subordinate. “Bridging Raw NWP Forecasts and Actionable Rainfall Intelligence” and “Explore forecast intelligence” sound like broad AI SaaS positioning; the precise GEFS/IMD research context should have more visual authority in a later redesign. Strength: the two tracks are explicitly separated, and the contrary extreme-FSS caveat is not hidden.

### Forecast — deep review

The side-by-side Raw GEFS / M1 Ridge MOS / IMD observed maps are the most credible workstation element. Common geography, synchronized map framing, units, and an inspector concept are valuable. Yet five primary selects, INIT/LEAD/IMD DATE/ROLE micro metadata, two basemap/display selects, overlay slider, boundaries checkbox, and four map tool icons consume the top 300px; maps start around 399px on a 1440×900 capture. Map titles use small text, and model colors are only tiny squares. The black/dark geographic basemap and dense place labels can compete with the muted blue rainfall raster; the “Weather Visualization” style resembles a polished GIS demo more than a calibrated scientific plate. The legend and point inspector fall below the initial viewport. When geography tiles have not loaded, “Loading geography” overlays the raster and weakens the comparison; the settled capture is the basis of this review. The control hierarchy should later distinguish dataset selection from map styling and keep quantitative comparison in the foreground.

### Casebook

It behaves like an archive by listing dated cases and exposing month, lead, observed event, regime, and outcome filters. Visually it is a repeated stack of large bordered rows with a date at far left and a small outcome summary near the middle, leaving broad unused space (`dark-1440-casebook.png`). It lacks the rhythm of a research event log or searchable evidence table. Six equal-weight filters and the same context strip make the archive feel like another dashboard page.

### Extreme Rain

The threshold and probability/detection/spatial-skill/reliability controls are scientifically meaningful. The first view is dominated by two tiers of button tabs and five boxed Brier/BSS/PR-AUC/ROC-AUC/event-count metrics before the probability map appears (`dark-1440-extremes.png`). The map is a strong domain-specific instrument but is demoted below BI-style tiles. Threshold semantics and high FAR caveats are present; the small caveat strip feels weaker than the positive tile numbers.

### Ensemble

Five-member subset scope is stated clearly. Case/member controls, three forecast maps, selected-cell member distribution, and matched-population probability comparison support a genuine uncertainty workflow. The first viewport still follows the same title/strip/select/cards pattern; the five-member caveat is only an 11px note inside a bordered panel. This page needs a stronger relationship between spread, selected cell, and paired reference; repeated nested surfaces currently split that story.

### Regimes

The pseudo-regime caveat is honest. The selected-case classifier probabilities and forecast-to-routing pathway have a distinct scientific purpose, yet the main view is a very large generic panel containing thin horizontal bars and another muted caveat band. The bars' visual weight is tiny relative to their container; labels and percentages are small. “Regime Intelligence” and “Selected case · classifier probabilities” feel like a dashboard feature label rather than a serious atmospheric-classification analysis.

### Districts

On the 2025 route, the page explicitly refuses to fabricate a missing district product—a scientific strength. Visually, the unsupported state is a modest card in the upper-left with most of the canvas empty (`dark-1440-districts.png`). The route feels unfinished even though the boundary is correct. The 2019 implementation has a district map/table and is the appropriate analytical personality; the default 2025 state does not lead users toward it strongly enough.

### Verification — deep review

The page contains genuine scientific comparison: a 2019 model ladder with RMSE/MAE/Bias/CSI, charts, FSS, reliability, and an explicit note that raw GEFS retains extreme-skill advantages. The first viewport, however, starts with another oversized `9.73% lower RMSE` headline card before the model table; the chart region begins below the fold. The same result appears on Overview, reducing Verification's identity as a lab. The RMSE Recharts bar chart uses five categorical colors and axis labels but no direct bar-end values or immediate role key; the color sequence feels like BI tooling (`dark-1440-verification-charts.png`). Dotted grids and default Recharts legend/tooltip structures are visible, though tooltip surfaces have CSS token styling. The paired Brier tiles beside the chart repeat the metric-card pattern. The 2019/2025 separation is semantically careful, but the dense 11px notes and visually dominant result need a more study-like hierarchy. On mobile, the 670px model table scrolls within its wrapper; this is expected, though the visible first two columns give little cue that more metrics exist to the right.

### Observations

The month×year matrix is the strongest distinct data artifact on the page. Before reaching it, six seasons are presented as two bordered lineage panels containing six smaller bordered year tiles, then another panel with four numeric boxes. The matrix competes with a card inventory for attention. Thin type and repeated uppercase role labels make it resemble an analytics report rather than an observation archive.

### Quality

The source-to-eligibility counts and year table are valuable provenance material. Four equal boxed numbers inside a large boxed section (1,125 / 1,125 / 615 / 218) read as SaaS KPI cards rather than a QC attrition chain (`light-1440-quality.png`). Repeated section cards (“By year,” packing reconstruction, read-only lineage) create strong surface fragmentation. The data table is precise; it should ultimately carry more of the page's hierarchy than the tiles.

### Methodology

The page's six-step pipeline is substantive. Visually, the “Every output has a documented lineage” hero repeats the Overview's two-column promotional composition, then the pipeline becomes six bordered mini cards with arrows (`dark-1440-methodology.png`). Some cells contain long explanatory text in ~11px. This feels like a pitch-deck architecture slide, not a readable scientific method. The final-test timeline below is useful but another three-card system.

### Audit

The 2023→2024→FREEZE→2025→CONSUMED lifecycle communicates governance clearly, but each stage is another bordered rectangle inside an analysis card. The read-only DAG and inspector are domain-specific; the surrounding sections again use the same rounded panel shell and teal left-border inspector (`dark-1440-audit.png`). Dense 11px metadata reduces trust-building legibility. “Scientific Audit” is accurate as an internal label, but the visual language is closer to a status console than an audit record.

## Maps, charts, tables, icons, badges, and microcopy

**Maps.** The paired geospatial data, same-domain comparison, labeled source/model roles, source-specific raster and legend are credible. Framing is card-like; basemap labels can overpower data, rainfall blue/cyan is low separation on the dark basemap, tiny header dots carry too much model identity, and units/legend/inspector are separated from the maps by vertical scroll. Map controls use generic `Plus/Minus/Rotate/Maximize` icons (`maps/map-controls.tsx`), which are understandable but visually similar to any web map. The 2019 provenance drawer is useful but its 330px sheet and blurred background are a generic app pattern (`dark-1440-provenance-drawer.png`).

**Charts.** Shared `ChartFrame` creates stable SVGs and captions (`science/chart-frame.tsx`). CSS styles the default Recharts tooltip, but axis/grid/Legend shapes still read as stock Recharts. The RMSE bar chart's flat five-color category palette raises the visual temperature relative to the otherwise muted page. FSS and reliability line work is scientifically appropriate; captions and sample caveats are 11px and require sustained reading. The chart frames are not blank in settled captures.

**Tables.** `science-table` and `phase5-table` use tabular numerals, right-aligned numeric values, clear headers, and row hover (`globals.css:276,345,479-481`): strong basics. The 12.5px effective text and 11px mono headers are small for public presentation. Mobile horizontal scrolling is contained but visually under-signaled. “Best 2019 RMSE” inline badge adds emphasis that a simple comparison marker or table note could carry later.

**Icons.** Lucide is consistent in stroke language, but icons appear on every nav item, most toolbar actions, state messages, and status rows. Gauge/Compass/Orbit/Network/Microscope are familiar generic product metaphors rather than a meteorological glyph vocabulary. Retain icons where they afford an action; a later design phase should question decorative repetition.

**Badges/pills.** Inventory: sidebar “Historical prototype” pill; per-page outlined `PrototypeNote`; data-source chips; active segmented tabs; model/result inline badge; uppercase role/context bands; threshold buttons. The status content is often scientifically necessary, but encoding almost every piece as a box/pill makes evidence and limitations compete with UI chrome. `PrototypeNote` appears repeatedly even when an adjacent context strip repeats “not live” or “historical.”

**Microcopy.** Scientific caveats are substantially better than marketing dashboards. Less convincing phrases include “Forecast & Atmosphere,” “Regime Intelligence,” “District Intelligence,” “Explore forecast intelligence,” “Bridging Raw NWP Forecasts and Actionable Rainfall Intelligence,” and generic “Scientific workspace.” They signal a broad AI product more than the exact experiment or analytical task. The report does **not** authorize copy edits or changes to numbers, caveats, model labels, or claims.

## Light mode, dark mode, and responsive design

**Light mode** has readable dark text and a clearer separation between data and basemap, but pale blue-gray background + white cards + teal CTA + soft shadows feels like a conventional SaaS admin theme. Borders are visible; nested surfaces still fragment Quality, Overview, and Observations. The map's grayscale/blue raster has limited separation from pale geography in some low-rain cells (`light-1440-forecast.png`).

**Dark mode** is visually coherent and comfortable in low light, but `#0a141d` background, `#12232e` cards, `#7bd3c5` primary, cyan raw/model traces, and lilac observed/model colors create the exact navy/teal/cyan/purple palette associated with AI dashboards. There is no gratuitous neon glow; the issue is the dominance of this familiar combination over a domain-specific visual language. Extreme-event map probabilities add violet to an already colorful scientific layer stack.

**Responsive.** The new 390px two-row header and drawer are compact and functional (`dark-390-mobile-drawer.png`). Cards, charts, and tables stack without settled document overflow in the captured matrix; large Verification tables scroll internally. The mobile first viewport still spends much of its height on heading, subtitle, prototype note, and headline metric before comparative evidence (`dark-390-verification.png`). At 1366px, the full sidebar remains visible, which helps navigation but leaves narrow chart/map widths. The design should be evaluated at realistic projector/laptop zoom and text scaling in a later implementation phase; this audit did not run an exhaustive zoom/contrast matrix.

## Design maturity scorecard

Scores are subjective, 1–10; **AI-template feeling is reversed** (10 = extremely template-like).

| Dimension | Score | Evidence |
|---|---:|---|
| Visual identity | 4 | Familiar navy/teal admin system; limited domain character. |
| Typography | 3 | Declared fonts not effectively applied; 84 literal 11px size declarations. |
| Color palette | 4 | Consistent but strongly associated with AI/developer dashboards. |
| Layout | 6 | Stable grid, maps/tables connected, instrument priority often weak. |
| Spacing | 5 | Token scale exists; extensive legacy one-off values remain. |
| Alignment | 6 | Mostly sound; small metadata and mixed card heights interrupt rhythm. |
| Information hierarchy | 5 | Large metric cards overpower caveats, maps, and study context. |
| Sidebar | 5 | Usable but generic admin/navigation language. |
| Maps | 6 | Real paired data and controls; framing/legend priority needs work. |
| Charts | 5 | Render and encode data; Recharts defaults and BI color feel remain. |
| Tables | 6 | Numeric alignment is good; density/scroll cues need care. |
| Component consistency | 7 | Reuse is strong, but sameness is part of the problem. |
| Scientific credibility of presentation | 7 | Honest labels and limitations; visual emphasis sometimes contradicts caution. |
| Distinctiveness | 3 | Much of the shell could be reused by unrelated analytics software. |
| Professional maturity | 4 | Polished implementation with weak task-specific editorial direction. |
| AI-template feeling | **8** | Dark teal cards, KPI numbers, pills, caps mono, generic icon rail. |

## Top 20 priority problems (direction only; no implementation authorized)

| Rank | Priority | Route/component | Problem, why it matters, high-level direction |
|---:|---|---|---|
| 1 | **P0** | Story Mode | Full-screen dialog is clipped to 63px header containing block; presentation cannot be used. Restore true viewport presentation containment in a later implementation phase. |
| 2 | **P1** | Global type | Local font assets are declared but effective stacks remain Segoe/Cascadia; platform-dependent personality. Resolve the token/source conflict after type direction is approved. |
| 3 | **P1** | Overview | Giant RMSE percentage/CTA leads like an AI startup landing page; give experiment identity and study scope visual precedence. |
| 4 | **P1** | All science routes | Repeated heading/note/strip/card sequence erases task identity; organize pages around their primary analytical artifact. |
| 5 | **P1** | Dark theme | Navy + mint + cyan + lilac dominates; establish a more domain-specific hierarchy without changing scientific encoding casually. |
| 6 | **P1** | Global labels | 11px mono/caps prevalence makes caveats and metadata hard to read in presentation; distinguish true micro labels from explanatory content. |
| 7 | **P1** | Forecast | Maps start near 399px on 900px height; prioritize the comparison instrument above secondary style controls. |
| 8 | **P1** | Extreme Rain | Metric tile row precedes probability map and caveat is visually subordinate; center event definition, map, and verification reading. |
| 9 | **P1** | Quality | Four KPI cards represent attrition as dashboard success stats; make eligibility flow and table carry the narrative. |
| 10 | **P1** | Districts 2025 | Honest unsupported state leaves most canvas blank; make the limitation and available 2019 route feel intentional. |
| 11 | **P1** | Casebook | Repeated wide rows have weak metadata hierarchy and waste space; use archive/log information architecture. |
| 12 | **P1** | Verification | Repeated oversized RMSE headline competes with model table, FSS, and reliability; make the laboratory comparison primary. |
| 13 | **P2** | Charts | Five BI-style model colors/default tooltip/axis conventions feel generic; improve analytical encoding and direct labels. |
| 14 | **P2** | Observations | Boxed year tiles plus boxed stats bury the six-season matrix; elevate the matrix as the main artifact. |
| 15 | **P2** | Methodology | Hero + six cards resembles a deck slide; move toward readable scientific documentation structure. |
| 16 | **P2** | Audit | Boxed governance stages and teal inspector resemble a status console; use audit-record hierarchy and evidence references. |
| 17 | **P2** | Sidebar | Square-letter mark, Lucide-per-link, caps groups, and status pill look like admin chrome; define navigation from analysis workflows. |
| 18 | **P2** | Panels | 49 exact `--line` border declarations plus nested cards flatten surface hierarchy; reserve borders for meaningful containment. |
| 19 | **P2** | Badges/caveats | Prototype note, context strip, footer pill, inline badges repeat statuses; retain scientific caveats while simplifying treatment. |
| 20 | **P2** | Light theme and mobile tables | White SaaS cards and under-signaled horizontal table scroll reduce maturity; improve surface rhythm and comparison affordances. |

No replacement palette, font family, layout, or code-level solution is selected in this audit. The priorities above are a basis for an owner-approved design phase.

## Recommended design priorities

First restore the currently broken Story Mode interaction, then establish a deliberately chosen effective type system and a page hierarchy that puts maps, verification comparisons, tables, and provenance ahead of repeated dashboard furniture. Next resolve the shell's generic identity, the dark/light palette's overfamiliar associations, and the 11px metadata habit. Finally rationalize card, border, badge, chart, and table treatments. Scientific color semantics, numbers, caveats, and track boundaries are constraints throughout. This is an order of design work for later approval, not permission to implement it now.

## Existing design token inventory

| Token group | Effective current values |
|---|---|
| Background / raised / recessed | Light `#f4f7f8 / #ffffff / #edf3f5`; dark `#0a141d / #12232e / #0d1c26` |
| Border / primary text / muted text | Light `#cbd8dc / #14242e / #4d626d`; dark `#29404b / #e9f2f2 / #acc1c7` |
| Primary / secondary accent | Light teal `#006b6d`, raw blue `#27628a`, observed violet `#6d53a2`; dark mint `#7bd3c5`, raw blue `#78b7df`, observed lilac `#c1a9f2` |
| Positive / caution / negative | Light `#2f7a4f / #855414 / #b84654`; dark `#6fcf97 / #f2bd70 / #ef8792` |
| Display/body | Intended local Inter variable asset; **effective** Segoe UI Variable → Segoe UI → Inter → Arial |
| Mono | Intended local JetBrains Mono asset; **effective** Cascadia Code → Consolas → Liberation Mono |
| Type/spacing scale | `11, 12.5, 14, 15, 17, 20, 26, 32px`; `4, 8, 12, 16, 20, 24px` |
| Radius | `--radius-control:6px`, `--radius-surface:12px`; theme `6/8/12px`; legacy literals `2–10px` and `999px` |
| Shadows | Light `0 3px 12px rgba(25,49,59,.07)` / `0 12px 32px rgba(25,49,59,.13)`; dark `0 3px 12px rgba(0,0,0,.16)` / `0 12px 32px rgba(0,0,0,.28)` |
| Geometry | Sidebar 248px; desktop header 64px; top controls/select 34px; mobile two-row bar 52px + 52px with 44px targets; main surface padding generally 20–24px |

## Desired visual character — direction, not design selection

VarshaSetu should read as a **meteorological analysis workstation** whose hierarchy follows forecast issue/lead → paired spatial fields → event/uncertainty interpretation → verification → provenance. Reference categories are operational weather workstations, GIS analysis tools, scientific verification software, and research data portals. The character should be restrained, precise, data-led, and legible at projector scale. Scientific encodings, caveats, and uncertainty should remain explicit. This is a verbal brief only; it does not choose new colors, fonts, tokens, or layouts.

## Screenshot index

The table below is generated from the live `capture-index.json`. Paths are repo-relative ignored artifacts; every row is one saved PNG. The strongest external-review anchors are **Overview, Forecast, Extreme Rain, Verification, Quality, Methodology, and Audit** at 1440px in both themes. Interaction and scrolled evidence follows the primary matrix.

| Route | Theme | Viewport | File |
|---|---|---:|---|
| / | dark | 1440×900 | test-results/design-audit/dark-1440-overview.png |
| /forecast | dark | 1440×900 | test-results/design-audit/dark-1440-forecast.png |
| /casebook | dark | 1440×900 | test-results/design-audit/dark-1440-casebook.png |
| /extremes | dark | 1440×900 | test-results/design-audit/dark-1440-extremes.png |
| /ensemble | dark | 1440×900 | test-results/design-audit/dark-1440-ensemble.png |
| /regimes | dark | 1440×900 | test-results/design-audit/dark-1440-regimes.png |
| /districts | dark | 1440×900 | test-results/design-audit/dark-1440-districts.png |
| /verification | dark | 1440×900 | test-results/design-audit/dark-1440-verification.png |
| /observations | dark | 1440×900 | test-results/design-audit/dark-1440-observations.png |
| /quality | dark | 1440×900 | test-results/design-audit/dark-1440-quality.png |
| /methodology | dark | 1440×900 | test-results/design-audit/dark-1440-methodology.png |
| /audit | dark | 1440×900 | test-results/design-audit/dark-1440-audit.png |
| / | dark | 1920×1080 | test-results/design-audit/dark-1920-overview.png |
| /forecast | dark | 1920×1080 | test-results/design-audit/dark-1920-forecast.png |
| /extremes | dark | 1920×1080 | test-results/design-audit/dark-1920-extremes.png |
| /verification | dark | 1920×1080 | test-results/design-audit/dark-1920-verification.png |
| /quality | dark | 1920×1080 | test-results/design-audit/dark-1920-quality.png |
| /methodology | dark | 1920×1080 | test-results/design-audit/dark-1920-methodology.png |
| /audit | dark | 1920×1080 | test-results/design-audit/dark-1920-audit.png |
| / | dark | 1366×768 | test-results/design-audit/dark-1366-overview.png |
| /forecast | dark | 1366×768 | test-results/design-audit/dark-1366-forecast.png |
| /extremes | dark | 1366×768 | test-results/design-audit/dark-1366-extremes.png |
| /verification | dark | 1366×768 | test-results/design-audit/dark-1366-verification.png |
| /quality | dark | 1366×768 | test-results/design-audit/dark-1366-quality.png |
| /methodology | dark | 1366×768 | test-results/design-audit/dark-1366-methodology.png |
| /audit | dark | 1366×768 | test-results/design-audit/dark-1366-audit.png |
| / | dark | 390×844 | test-results/design-audit/dark-390-overview.png |
| /forecast | dark | 390×844 | test-results/design-audit/dark-390-forecast.png |
| /extremes | dark | 390×844 | test-results/design-audit/dark-390-extremes.png |
| /verification | dark | 390×844 | test-results/design-audit/dark-390-verification.png |
| /quality | dark | 390×844 | test-results/design-audit/dark-390-quality.png |
| /methodology | dark | 390×844 | test-results/design-audit/dark-390-methodology.png |
| /audit | dark | 390×844 | test-results/design-audit/dark-390-audit.png |
| / | light | 1440×900 | test-results/design-audit/light-1440-overview.png |
| /forecast | light | 1440×900 | test-results/design-audit/light-1440-forecast.png |
| /casebook | light | 1440×900 | test-results/design-audit/light-1440-casebook.png |
| /extremes | light | 1440×900 | test-results/design-audit/light-1440-extremes.png |
| /ensemble | light | 1440×900 | test-results/design-audit/light-1440-ensemble.png |
| /regimes | light | 1440×900 | test-results/design-audit/light-1440-regimes.png |
| /districts | light | 1440×900 | test-results/design-audit/light-1440-districts.png |
| /verification | light | 1440×900 | test-results/design-audit/light-1440-verification.png |
| /observations | light | 1440×900 | test-results/design-audit/light-1440-observations.png |
| /quality | light | 1440×900 | test-results/design-audit/light-1440-quality.png |
| /methodology | light | 1440×900 | test-results/design-audit/light-1440-methodology.png |
| /audit | light | 1440×900 | test-results/design-audit/light-1440-audit.png |
| / | light | 1920×1080 | test-results/design-audit/light-1920-overview.png |
| /forecast | light | 1920×1080 | test-results/design-audit/light-1920-forecast.png |
| /extremes | light | 1920×1080 | test-results/design-audit/light-1920-extremes.png |
| /verification | light | 1920×1080 | test-results/design-audit/light-1920-verification.png |
| /quality | light | 1920×1080 | test-results/design-audit/light-1920-quality.png |
| /methodology | light | 1920×1080 | test-results/design-audit/light-1920-methodology.png |
| /audit | light | 1920×1080 | test-results/design-audit/light-1920-audit.png |
| / | light | 1366×768 | test-results/design-audit/light-1366-overview.png |
| /forecast | light | 1366×768 | test-results/design-audit/light-1366-forecast.png |
| /extremes | light | 1366×768 | test-results/design-audit/light-1366-extremes.png |
| /verification | light | 1366×768 | test-results/design-audit/light-1366-verification.png |
| /quality | light | 1366×768 | test-results/design-audit/light-1366-quality.png |
| /methodology | light | 1366×768 | test-results/design-audit/light-1366-methodology.png |
| /audit | light | 1366×768 | test-results/design-audit/light-1366-audit.png |
| / | light | 390×844 | test-results/design-audit/light-390-overview.png |
| /forecast | light | 390×844 | test-results/design-audit/light-390-forecast.png |
| /extremes | light | 390×844 | test-results/design-audit/light-390-extremes.png |
| /verification | light | 390×844 | test-results/design-audit/light-390-verification.png |
| /quality | light | 390×844 | test-results/design-audit/light-390-quality.png |
| /methodology | light | 390×844 | test-results/design-audit/light-390-methodology.png |
| /audit | light | 390×844 | test-results/design-audit/light-390-audit.png |

### Interaction and scrolled evidence

| Route / state | Theme | Viewport | File |
|---|---|---:|---|
| / — Story Mode | dark | 1440×900 | test-results/design-audit/dark-1440-story-mode.png |
| / — Presentation View | dark | 1440×900 | test-results/design-audit/dark-1440-presentation-view.png |
| /forecast — 2019 provenance drawer | dark | 1440×900 | test-results/design-audit/dark-1440-provenance-drawer.png |
| / — mobile nav drawer | dark | 390×844 | test-results/design-audit/dark-390-mobile-drawer.png |
| /verification — charts | dark | 1440×900 | test-results/design-audit/dark-1440-verification-charts.png |
| /verification — charts | light | 1440×900 | test-results/design-audit/light-1440-verification-charts.png |
| /forecast — map/legend transient geography state | dark | 1440×900 | test-results/design-audit/dark-1440-forecast-legend-inspector.png |
| /audit — lineage | dark | 1440×900 | test-results/design-audit/dark-1440-audit-lineage.png |
| /observations — matrix | light | 1440×900 | test-results/design-audit/light-1440-observations-matrix.png |
| /regimes — probability bars | dark | 1440×900 | test-results/design-audit/dark-1440-regimes-bars.png |
| /ensemble — analysis | dark | 1440×900 | test-results/design-audit/dark-1440-ensemble-analysis.png |

The transient Forecast detail capture records map-geography loading and is not the settled map baseline; use the primary Forecast matrix for final-map evaluation.

## Files changed

- `docs/105_VISUAL_DESIGN_AND_AI_SLOP_AUDIT.md` (this report).
- `docs/00_INDEX.md` (documentation index entry).
- Ignored `test-results/design-audit/` screenshots, scripts, and JSON evidence.

**No frontend source files changed. No scientific files changed. No design changes implemented.**
