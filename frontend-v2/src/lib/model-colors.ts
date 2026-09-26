// Phase 5A.3: one canonical model-color map (CSS custom properties defined
// in globals.css :root/.dark), used consistently across Forecast/
// Verification/Extremes/Story Mode/Skill Cube instead of each component
// picking its own colors. Deliberately a separate namespace from the
// semantic (meaning) colors -- a model's color never doubles as a
// "caution"/"positive" signal.
export const MODEL_ORDER = ["M0", "M1", "M2", "M3", "M4"] as const;
export type ModelKey = (typeof MODEL_ORDER)[number];

export const MODEL_COLOR: Record<ModelKey, string> = {
  M0: "var(--model-m0)", M1: "var(--model-m1)", M2: "var(--model-m2)", M3: "var(--model-m3)", M4: "var(--model-m4)",
};
export const IMD_COLOR = "var(--model-imd)";

export const MODEL_LABEL: Record<ModelKey, string> = {
  M0: "Raw GEFS", M1: "Ridge MOS", M2: "Global XGBoost", M3: "Hard regime routing", M4: "Soft regime mixture",
};
export const MODEL_ROLE: Record<ModelKey, string> = {
  M0: "Raw reference", M1: "Preselected primary 2025 model", M2: "Secondary 2025 result", M3: "Predeclared secondary", M4: "Predeclared secondary",
};

export const SEMANTIC_COLOR = {
  positive: "var(--semantic-positive)", caution: "var(--semantic-caution)", negative: "var(--semantic-negative)", info: "var(--semantic-info)",
} as const;
