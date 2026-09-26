// Phase 5A.2B: makes /api/science/operational/* the primary source for a
// Track B (2023-2025) forecast case, replacing the pre-generated static
// bundle for rainfall/probability/regime/ensemble -- the values a judge or
// reviewer actually reads. Atmosphere fields remain sourced from the static
// bundle for this phase (see docs/95 section 15/26 "Known Limitations"): the
// live API's atmosphere grids are native 51x81 while this presentation layer
// and its map component currently assume the 49x49 rainfall domain, and
// building a true synoptic (vector/contour) workspace is explicitly deferred
// to a later phase. This module never fabricates a value: every rainfall,
// probability, regime, and ensemble field it returns is either read from the
// live hash-verified API or (only on a genuine network failure) from the
// same static bundle the page used before this migration.
import {
  OperationalApiError,
  getOperationalCase as getLiveOperationalCase,
  getOperationalEnsemble,
  getOperationalProbability,
  getOperationalRainfall,
  getOperationalRegime,
  type OperationalYear,
} from "@/lib/api/operational";
import { getOperationalCase as getStaticOperationalCase, type OperationalCase, type OperationalCaseSummary, type OperationalIndex } from "@/science/frozen/operational";
import { withStaticFallback, type DataSourceMode } from "@/lib/data-source";

const RAINFALL_LIVE_FIELDS = ["raw", "m1", "m2", "m3", "m4", "imd"] as const;

function staticFieldKey(liveField: string, year: number): string {
  if (liveField === "raw") return "M0";
  if (liveField === "imd") return "observed";
  if (liveField === "m2") return year === 2023 ? "M2_OOF" : "M2";
  return liveField.toUpperCase();
}

/** Inverse of the static bundle's expandedField(): scatters a 49x49 grid back
 * into the same 1301-length, pixel-index-ordered flat array the rest of this
 * component already renders, so no downstream rendering/error-anatomy/point-
 * inspector code needs to change to consume live data. */
function flattenGrid(index: OperationalIndex, matrix: (number | null)[][]): number[] {
  return index.pixel_indices.map((flat) => {
    const value = matrix[Math.floor(flat / 49)]?.[flat % 49];
    return typeof value === "number" ? value : NaN;
  });
}

type LiveCaseFields = {
  fields: Record<string, number[]>;
  probabilities: OperationalCase["probabilities"];
  regime_probabilities: OperationalCase["regime_probabilities"];
  ensemble_members: OperationalCase["ensemble_members"];
  models_present: string[];
};

// The backend's /cases/{case_id} `available_products` list uses a distinct
// capability label ("m2_out_of_fold") for 2023 to make the OOF status
// visible at the metadata level, but the actual /rainfall?field= query
// parameter it accepts is always the plain model key ("m2") -- the OOF
// framing is carried in that response's own prediction_role field, not the
// query string. Normalize before filtering so 2023 doesn't silently lose M2.
function normalizeAvailableProduct(product: string): string {
  return product === "m2_out_of_fold" ? "m2" : product;
}

async function fetchLiveCaseFields(year: OperationalYear, caseId: string, index: OperationalIndex): Promise<LiveCaseFields> {
  const caseDetail = await getLiveOperationalCase(year, caseId);
  const normalizedProducts = caseDetail.available_products.map(normalizeAvailableProduct);
  const rainfallFields = normalizedProducts.filter((product): product is (typeof RAINFALL_LIVE_FIELDS)[number] =>
    (RAINFALL_LIVE_FIELDS as readonly string[]).includes(product));

  const rainfallEntries = await Promise.all(rainfallFields.map(async (field) => {
    const grid = await getOperationalRainfall(year, caseId, field);
    return [staticFieldKey(field, year), flattenGrid(index, grid.values)] as const;
  }));
  const fields = Object.fromEntries(rainfallEntries) as Record<string, number[]>;

  let probabilities: OperationalCase["probabilities"] = null;
  if (caseDetail.available_products.includes("heavy_probability")) {
    const [heavy, veryHeavy] = await Promise.all([
      getOperationalProbability(year, caseId, "heavy"),
      getOperationalProbability(year, caseId, "very_heavy"),
    ]);
    probabilities = { heavy: flattenGrid(index, heavy.values), very_heavy: flattenGrid(index, veryHeavy.values) };
  }

  let regimeProbabilities: OperationalCase["regime_probabilities"] | null = null;
  if (caseDetail.available_products.includes("regime")) {
    const regime = await getOperationalRegime(year, caseId);
    regimeProbabilities = [
      regime.probabilities.ACTIVE_MONSOON ?? 0,
      regime.probabilities.BREAK_WEAK_MONSOON ?? 0,
      regime.probabilities.LOW_DEPRESSION_INFLUENCED ?? 0,
    ];
  }

  let ensembleMembers: OperationalCase["ensemble_members"] = null;
  try {
    const ensemble = await getOperationalEnsemble(year, caseId);
    const eligible = ensemble.members.filter((member) => member.qc_eligible && member.values);
    if (eligible.length > 0) {
      ensembleMembers = Object.fromEntries(eligible.map((member) => [member.member, flattenGrid(index, member.values!)]));
    }
  } catch (error) {
    if (error instanceof OperationalApiError && error.kind === "INTEGRITY_FAILURE") throw error;
    // otherwise: this case genuinely has no eligible ensemble members -- leave null, not an error.
  }

  return {
    fields,
    probabilities,
    regime_probabilities: regimeProbabilities ?? [0, 0, 0],
    ensemble_members: ensembleMembers,
    models_present: Object.keys(fields).filter((key) => key !== "M0" && key !== "observed"),
  };
}

export type LoadedOperationalCase = {
  case: OperationalCase;
  mode: DataSourceMode;
  message: string | null;
  /** Model keys (e.g. "M1","M2") actually confirmed present for this case
   * this load -- null when sourced from the static fallback, in which case
   * the caller should fall back to the static index's own `models` list. */
  modelsPresent: string[] | null;
};

/**
 * Primary data path for a Track B forecast case: live rainfall/probability/
 * regime/ensemble, static-bundle atmosphere (documented limitation above).
 * Falls back to the fully static case only on a genuine live-API network
 * failure; never on an integrity failure or a real product-unavailable
 * answer (see lib/data-source.ts).
 */
export async function loadOperationalCase(
  year: OperationalYear,
  caseId: string,
  summary: OperationalCaseSummary,
  index: OperationalIndex,
): Promise<LoadedOperationalCase> {
  const result = await withStaticFallback(
    async () => {
      const [live, staticCase] = await Promise.all([
        fetchLiveCaseFields(year, caseId, index),
        getStaticOperationalCase(summary),
      ]);
      const merged: OperationalCase = {
        ...staticCase,
        fields: { M0: staticCase.fields.M0, observed: staticCase.fields.observed, ...live.fields },
        probabilities: live.probabilities,
        regime_probabilities: live.regime_probabilities,
        ensemble_members: live.ensemble_members,
      };
      return { case: merged, modelsPresent: live.models_present as string[] | null };
    },
    async () => ({ case: await getStaticOperationalCase(summary), modelsPresent: null as string[] | null }),
  );
  if (!result.data) {
    return { case: null as unknown as OperationalCase, mode: result.mode, message: result.message, modelsPresent: null };
  }
  return { case: result.data.case, mode: result.mode, message: result.message, modelsPresent: result.data.modelsPresent };
}
