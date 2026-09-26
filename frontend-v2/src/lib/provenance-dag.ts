// Phase 5A.3, section 34-35: static provenance/lineage metadata for the
// Track-B (2023-2025 historical operational GEFS) model DAG. This is
// documentation of an already-frozen pipeline (docs/86-91), not a live
// query -- the DAG shape and every field here describes what the frozen
// artifacts already are, never a path on this machine (no absolute local
// paths, per section 35).
export type ProvenanceNode = {
  id: string;
  label: string;
  row: number;
  dependsOn: string[];
  stage: string;
  inputSource: string;
  outputArtifactType: string;
  yearRole?: string;
  featureCount?: string;
  modelFamily?: string;
  scientificStatus: string;
  integrityStatus: string;
  docReference: string;
};

export const PROVENANCE_NODES: ProvenanceNode[] = [
  { id: "gefs", label: "NOAA GEFS", row: 0, dependsOn: [], stage: "Source acquisition", inputSource: "Historical NOAA operational GEFS, selected byte ranges", outputArtifactType: "Raw GRIB2 messages", scientificStatus: "Frozen source", integrityStatus: "Hash-verified on acquisition", docReference: "docs/85_OPERATIONAL_CORPUS_PAYLOAD_ACQUISITION.md" },
  { id: "selection", label: "Message Selection", row: 1, dependsOn: ["gefs"], stage: "Selection", inputSource: "Acquired GRIB2 messages", outputArtifactType: "00 UTC init, 3 lead products, available rainfall members", scientificStatus: "Frozen selection rule", integrityStatus: "Deterministic filter, hash-verified", docReference: "docs/84_OPERATIONAL_CORPUS_SOURCE_INVENTORY.md" },
  { id: "decode", label: "Decode", row: 2, dependsOn: ["selection"], stage: "Decoding", inputSource: "Selected GRIB2 messages", outputArtifactType: "Decoded numeric arrays (canonical accumulation-aware reconstruction)", scientificStatus: "Frozen decoder", integrityStatus: "Hash-verified per-message", docReference: "docs/42_GEFS_ACCUMULATION_ANOMALY_REPORT.md" },
  { id: "qc", label: "QC", row: 3, dependsOn: ["decode"], stage: "Quality control", inputSource: "Decoded arrays", outputArtifactType: "QC-eligible case/member flags", scientificStatus: "Frozen QC policy", integrityStatus: "Deterministic, reproduces stored eligibility", docReference: "docs/41_MONTHLY_QC_SPEC.md" },
  { id: "features", label: "Rainfall / Atmosphere Features", row: 4, dependsOn: ["qc"], stage: "Feature construction", inputSource: "QC-eligible decoded arrays", outputArtifactType: "Forecast-time feature cache (49x49 rainfall target + 6 atmosphere fields)", featureCount: "22 forecast-time deterministic features", scientificStatus: "Frozen feature build", integrityStatus: "Hash-verified feature cache", docReference: "docs/86_OPERATIONAL_FEATURE_DATASET_2023_2025.md" },
  { id: "m1", label: "M1", row: 5, dependsOn: ["features"], stage: "Deterministic model", inputSource: "Forecast-time feature cache", outputArtifactType: "Per-case rainfall grid", modelFamily: "Linear Ridge MOS", yearRole: "2023 fit, 2024 selected, 2025 final-test evaluated", scientificStatus: "PRESELECTED PRIMARY 2025 MODEL", integrityStatus: "Frozen weights, hash-verified", docReference: "docs/89_OPERATIONAL_FINAL_TEST_2025.md" },
  { id: "m2", label: "M2", row: 5, dependsOn: ["features"], stage: "Deterministic model", inputSource: "Forecast-time feature cache", outputArtifactType: "Per-case rainfall grid", modelFamily: "Global XGBoost (non-regime)", yearRole: "2023 fit, 2024 secondary, 2025 SECONDARY final-test result", scientificStatus: "Secondary comparison only -- not eligible for post-test reselection as primary", integrityStatus: "Frozen weights, hash-verified", docReference: "docs/89_OPERATIONAL_FINAL_TEST_2025.md" },
  { id: "regime", label: "Regime Classifier", row: 6, dependsOn: ["m2", "features"], stage: "Regime routing input", inputSource: "Forecast-time feature cache (forecast-only diagnostics)", outputArtifactType: "3-class forecast-only pseudo-regime probability vector per case", modelFamily: "Forecast-only pseudo-label classifier", scientificStatus: "Forecast-only pseudo-regime, not observed meteorological truth", integrityStatus: "Frozen classifier, hash-verified", docReference: "docs/54_PROTOTYPE_REGIME_METHODOLOGY.md" },
  { id: "m3", label: "M3", row: 7, dependsOn: ["regime", "m1", "m2"], stage: "Regime-aware model", inputSource: "Regime probabilities + M1/M2 outputs", outputArtifactType: "Per-case rainfall grid", modelFamily: "Hard regime routing", scientificStatus: "Predeclared secondary comparator; did not beat M2 overall", integrityStatus: "Frozen weights, hash-verified", docReference: "docs/61_REGIME_AWARE_BENEFIT_ANALYSIS.md" },
  { id: "m4", label: "M4", row: 7, dependsOn: ["regime", "m1", "m2"], stage: "Regime-aware model", inputSource: "Regime probabilities + M1/M2 outputs", outputArtifactType: "Per-case rainfall grid", modelFamily: "Soft regime mixture-of-experts", scientificStatus: "Predeclared secondary comparator; beat hard routing, not M2", integrityStatus: "Frozen weights, hash-verified", docReference: "docs/61_REGIME_AWARE_BENEFIT_ANALYSIS.md" },
  { id: "probability", label: "Heavy / Very Heavy Probability Models", row: 8, dependsOn: ["m2", "regime", "features"], stage: "Probability modeling", inputSource: "22 forecast features + M2 correction + 3 pseudo-regime probabilities", outputArtifactType: "Per-case Heavy/Very-Heavy probability grid", featureCount: "26 inputs", scientificStatus: "Frozen probability models", integrityStatus: "Frozen weights, hash-verified", docReference: "docs/63_EXTREME_RAIN_PROBABILITY_MODELING.md" },
  { id: "calibration", label: "Calibration", row: 9, dependsOn: ["probability"], stage: "Probability calibration", inputSource: "Raw probability model output", outputArtifactType: "Isotonic/logistic-calibrated probability grid", scientificStatus: "Frozen calibrator, selected before 2025 unsealed", integrityStatus: "Frozen calibrator, hash-verified", docReference: "docs/63_EXTREME_RAIN_PROBABILITY_MODELING.md" },
  { id: "verification", label: "Verification", row: 10, dependsOn: ["m1", "m2", "m3", "m4", "calibration"], stage: "Verification", inputSource: "All model outputs + paired IMD observations", outputArtifactType: "Continuous, categorical, probabilistic and 2-D FSS metrics", scientificStatus: "One-time 2025 final-test evaluation", integrityStatus: "Hash-verified against frozen predictions and observations", docReference: "docs/89_OPERATIONAL_FINAL_TEST_2025.md" },
  { id: "frozen", label: "Frozen Results", row: 11, dependsOn: ["verification"], stage: "Frozen result", inputSource: "Verification output", outputArtifactType: "FINAL_TEST_RESULT (sealed, independently audited)", scientificStatus: "Consumed once; no post-hoc model-development revision", integrityStatus: "Hash-verified; independently reproduced (Phase 4K)", docReference: "docs/90_INDEPENDENT_FINAL_SCIENTIFIC_AUDIT.md" },
];
