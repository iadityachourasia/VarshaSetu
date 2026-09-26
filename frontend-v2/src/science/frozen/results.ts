import final2025 from "../../../public/science/operational-v1/final_result_2025.json";
import validation2024 from "../../../public/science/operational-v1/validation_metrics_2024.json";
import probabilityValidation2024 from "../../../public/science/operational-v1/probability_validation_2024.json";
import presentationManifest from "../../../public/science/operational-v1/presentation_science_manifest.json";

export { final2025, validation2024, probabilityValidation2024, presentationManifest };

export const modelNames: Record<string, string> = {
  M0: "Raw GEFS", M1: "Ridge MOS", M2: "Global XGBoost", M3: "Hard regime routing", M4: "Soft regime mixture",
};
export const regimeNames = ["Active Monsoon", "Break / Weak Monsoon", "Low / Depression Influenced"] as const;
export const thresholds = { heavy: 64.5, veryHeavy: 115.6 } as const;
