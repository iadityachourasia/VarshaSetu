---
name: VarshaSetu
description: A disciplined scientific workspace for historical monsoon rainfall post-processing evidence.
colors:
  canvas-navy: "#0a141d"
  raised-slate: "#12232e"
  recessed-navy: "#0d1c26"
  sidebar-navy: "#0d1b25"
  text-ice: "#e9f2f2"
  text-muted: "#acc1c7"
  rule-slate: "#29404b"
  action-teal: "#7bd3c5"
  raw-blue: "#78b7df"
  observed-violet: "#c1a9f2"
  caution-amber: "#f2bd70"
  danger-rose: "#ef8792"
  map-navy: "#0b1a25"
typography:
  display:
    fontFamily: "Segoe UI Variable, Segoe UI, Inter, Arial, sans-serif"
    fontSize: "clamp(38px, 4.2vw, 65px)"
    fontWeight: 670
    lineHeight: 1
    letterSpacing: "-0.065em"
  headline:
    fontFamily: "Segoe UI Variable, Segoe UI, Inter, Arial, sans-serif"
    fontSize: "25px"
    fontWeight: 650
    lineHeight: 1.1
    letterSpacing: "-0.025em"
  title:
    fontFamily: "Segoe UI Variable, Segoe UI, Inter, Arial, sans-serif"
    fontSize: "15px"
    fontWeight: 650
    letterSpacing: "-0.015em"
  body:
    fontFamily: "Segoe UI Variable, Segoe UI, Inter, Arial, sans-serif"
    fontSize: "12px"
  label:
    fontFamily: "Cascadia Code, Consolas, Liberation Mono, monospace"
    fontSize: "10px"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "0.075em"
rounded:
  sm: "4px"
  control: "5px"
  md: "7px"
  panel: "8px"
  lg: "10px"
spacing:
  tight: "8px"
  panel-gap: "12px"
  content-x: "28px"
components:
  button-primary:
    backgroundColor: "{colors.action-teal}"
    textColor: "{colors.canvas-navy}"
    rounded: "{rounded.control}"
    padding: "12px 16px"
  icon-button:
    backgroundColor: "transparent"
    textColor: "{colors.text-ice}"
    rounded: "6px"
    size: "30px"
  case-selector:
    backgroundColor: "{colors.raised-slate}"
    textColor: "{colors.text-ice}"
    rounded: "{rounded.panel}"
    padding: "12px 13px"
  map-panel:
    backgroundColor: "{colors.raised-slate}"
    textColor: "{colors.text-ice}"
    rounded: "{rounded.panel}"
  input-select:
    backgroundColor: "{colors.recessed-navy}"
    textColor: "{colors.text-ice}"
    rounded: "{rounded.control}"
    padding: "7px 24px 7px 9px"
---

# Design System: VarshaSetu

## Overview

**Creative North Star: "The Scientific Operations Desk"**

VarshaSetu is a compact, code-led place to inspect historical forecast evidence. Near-navy surfaces, fine rules, precise typography, and small teal interaction cues give maps and measurements the dominant visual role. Its atmosphere is institutional, serious, and restrained.

The interface communicates scientific lineage and uncertainty at the point of use. Forecast fields, reference observations, regime probabilities, and held-out verification remain visibly distinct. The visual system supports a read-only historical prototype; it does not imply current operational forecasting.

**Key Characteristics:**

- Dark-first scientific canvas with a semantic light counterpart.
- Dense, aligned maps and tables with shared scales and explicit units.
- Compact metadata in a system mono stack; measured headings in a system sans stack.
- Teal for interaction, with distinct blue, teal, and violet identities for raw, corrected, and observed fields.

## Colors

The palette is cool and low-glare, with scientific data colors reserved for identifiable fields and legends. The dark values above are the primary presentation; `globals.css` defines light semantic counterparts using the same roles.

### Primary

- **Action Teal:** Used for primary actions, active navigation, selected states, focus, and corrected-forecast identity. It should mark interaction or the corrected series, not arbitrary decoration.

### Secondary

- **Raw Blue:** Identifies raw GEFS in map headings and comparisons.
- **Observed Violet:** Identifies the IMD observation/reference field.

### Tertiary

- **Caution Amber:** Flags scientific limitations and heavy-event emphasis.
- **Danger Rose:** Reserved for stronger warnings and very-heavy-event emphasis.

### Neutral

- **Canvas Navy:** Full-page ground.
- **Raised Slate:** Panels, case controls, tables, and inspector surfaces.
- **Recessed Navy:** Header and field wells.
- **Sidebar Navy:** Navigation rail.
- **Text Ice / Text Muted:** Primary reading and secondary metadata.
- **Rule Slate:** Thin separators and panel outlines.
- **Map Navy:** Neutral map plane beneath rainfall cells.

**The Scientific Color Rule.** Data colors keep stable meanings across routes. A raw/corrected/observed comparison uses the same identities and a shared rainfall scale; probability uses its own labeled scale.

## Typography

**Display Font:** Segoe UI Variable, falling back to Segoe UI, Inter, Arial, and sans-serif.

**Body Font:** The same local system sans stack.

**Label/Mono Font:** Cascadia Code, falling back to Consolas, Liberation Mono, and monospace.

**Character:** Condensed in rhythm rather than width: close-set headings, modest body copy, and precise monospaced metadata. Local system fonts avoid dependence on a remote font service.

### Hierarchy

- **Display:** Reserved for the Overview hero, where the large scale is justified by the landing context.
- **Headline:** Page title with compact line height and tracking.
- **Title:** Section heading or panel title.
- **Body:** Short explanation and limitation copy; scientific tables and panels may use smaller sizes when values remain readable.
- **Label:** Uppercase metadata and small field labels. Dates, coordinates, hashes, units, and compact legend ticks use the mono family.

**The Evidence First Rule.** Numeric values use tabular figures, explicit units, and nearby provenance or denominator context where the metric needs it.

## Layout

The desktop shell uses a left rail and a short contextual header. The rail is wide on large screens and reduces to an icon rail below 1550px. Main content is capped at 1900px. The Forecast Explorer places the case selector immediately above three equal map panels, followed by one shared rainfall legend and the cell, regime, and case-verification readouts. Panel gaps are tight and consistent.

At 1100px the map triptych wraps to two columns; at 760px it stacks into one column and navigation becomes a horizontal icon row. Case filters form a two-column mobile grid. Inspection and verification details follow the visual data instead of competing with it. The interface preserves exact values and labels on smaller screens rather than reducing scientific detail to decorative summary cards.

## Elevation & Depth

The workspace is flat by default. Tonal steps, thin borders, and panel containment establish depth. Small shadows appear only in selected segmented controls and a few overlay states; they are not a general card treatment. Motion is short and functional, with reduced-motion preferences respected.

**The Flat Evidence Rule.** Maps, tables, and notes gain hierarchy from alignment, borders, and surface tone; routine scientific panels do not float above the canvas.

## Shapes

The form language uses gently rounded control corners and restrained panel corners. Small badges and legend swatches are squarer. Borders are fine, continuous, and neutral. The maps themselves are square working planes within clipped panels; no ornamental shape competes with gridded data.

## Components

### Buttons

- **Shape:** Compact controls; primary links use the control radius, while icon buttons are square with slightly softened corners.
- **Primary:** Teal fill with dark text in dark mode; semantic token equivalents in light mode.
- **Hover / Focus:** Subtle surface or brightness change and a visible two-pixel focus outline with offset. Disabled buttons reduce opacity and suppress interaction.
- **Secondary / Ghost:** Fine outline or clear background for provenance and utility actions.

### Case Selector and Fields

- **Style:** One raised panel groups historical case navigation, lead, regime, and demo-case controls. Native selects sit on a recessed surface with fine borders and compact type.
- **Focus:** The global visible focus outline applies to every control, including selects.
- **Behavior:** Mobile controls wrap and expand to full available width rather than clipping their labels.

### Cards / Containers

- **Corner Style:** Small, consistent panel rounding.
- **Background:** Raised surface over the navy canvas.
- **Border:** One-pixel neutral rule; most scientific readouts use an open top divider instead of another boxed card.
- **Internal Padding:** Tight for map headings and selectors; larger where text explanation needs reading space.

### Navigation

- **Style:** Persistent side rail with compact icon-and-label links; active state uses a tonal fill and teal text. Below 1550px it becomes an icon rail, and below 760px a horizontal row. The current page is announced semantically.

### Synchronized Rainfall Maps

Three peer panels show Raw GEFS, VarshaSetu Corrected, and IMD Observed at the same extent and rainfall scale. Their map planes use the same paired valid-cell mask. One selected cell produces aligned raw, corrected, observed, and correction-difference values, with a keyboard-selectable row and column alternative. The shared legend labels rainfall in mm / 24 h.

### Verification Tables and Notes

Tables use tabular numbers, right-aligned measurements, and a restrained hover tint. Limitations are surfaced in narrow amber notes. Undefined or unavailable scientific values are written as such, never converted into zero for display.

## Do's and Don'ts

### Do:

- **Do** make source, valid period, lead, accumulation window, and observation identity visible around scientific outputs.
- **Do** keep raw, corrected, and observed rainfall visually comparable through common extent, mask, units, and legend.
- **Do** provide readable numeric alternatives to maps and preserve keyboard focus and reduced-motion behavior.
- **Do** pair a favorable metric with its held-out scope and relevant limitation.

### Don't:

- **Don't** imply the historical prototype is a current operational forecast.
- **Don't** use generic dashboard decoration, consumer-weather motifs, or animated marks as substitutes for scientific evidence.
- **Don't** invent metrics, probabilities, map values, or confidence labels in the interface.
- **Don't** use red and green alone to distinguish scientific series or event categories.
