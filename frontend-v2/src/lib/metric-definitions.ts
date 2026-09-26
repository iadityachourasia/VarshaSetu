// Phase 5A.3, section 59: one canonical definition source for every metric
// abbreviation used across the app, so a tooltip/label never drifts between
// pages. Definitions are the metric's formula/meaning, not a claim about
// this project's own results (no "our RMSE is good" framing here).
export const METRIC_DEFINITION: Record<string, string> = {
  RMSE: "Root Mean Squared Error, in mm. Penalizes large errors more than small ones. Lower is better.",
  MAE: "Mean Absolute Error, in mm. The average magnitude of forecast error, weighting all errors equally. Lower is better.",
  Bias: "Mean signed error (forecast minus observed), in mm. Positive = systematic over-forecast; negative = systematic under-forecast.",
  POD: "Probability of Detection: hits divided by (hits + misses). Fraction of observed events the forecast caught. Higher is better, but says nothing about false alarms.",
  FAR: "False Alarm Ratio: false alarms divided by (hits + false alarms). Fraction of forecast events that did not occur. Lower is better.",
  CSI: "Critical Success Index: hits divided by (hits + misses + false alarms). A single skill score for a binary event; 0 = no skill, 1 = perfect.",
  ETS: "Equitable Threat Score: CSI adjusted for the hits expected by random chance. Rewards skill beyond climatological guessing; 0 = no skill beyond chance.",
  FSS: "Fractions Skill Score: agreement between forecast and observed event fraction within a spatial neighborhood, not a single grid cell. 1 = perfect spatial match at that neighborhood size.",
  Brier: "Brier score: mean squared error of a probability forecast against the 0/1 observed outcome. Lower is better; 0 is perfect.",
  BSS: "Brier Skill Score: skill relative to a fixed reference probability (a climatological base rate here, not a competing model). Positive = better than that reference.",
  "PR-AUC": "Area under the Precision-Recall curve, as a single scalar (the curve itself is not rendered, only this number). Higher is better; more informative than ROC-AUC for rare events.",
  "ROC-AUC": "Area under the Receiver Operating Characteristic curve, as a single scalar. 0.5 = no better than random; 1.0 = perfect discrimination. Can look favorable even when precision is poor for a rare event.",
};

export type MetricAbbreviation = keyof typeof METRIC_DEFINITION;
