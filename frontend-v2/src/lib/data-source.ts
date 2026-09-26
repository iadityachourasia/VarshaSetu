// Phase 5A.2B: a small, reusable status model for "which source produced this
// value" -- the live hash-verified operational API is authoritative; the
// pre-generated static presentation bundle is a bounded fallback for when the
// API is unreachable, never a silent substitute for a real scientific
// unavailability or integrity failure. See docs/95 section 4-5 and 20 for the
// governing rules this module encodes.
import { OperationalApiError } from "./api/operational";

export type DataSourceMode =
  | "VERIFIED_API"
  | "VERIFIED_STATIC_FALLBACK"
  | "UNAVAILABLE"
  | "INTEGRITY_FAILURE"
  | "NETWORK_FAILURE";

export type DataSourceResult<T> = {
  mode: DataSourceMode;
  data: T | null;
  message: string | null;
};

const FALLBACK_MESSAGE = "Live API unreachable; showing cached frozen presentation data.";
const UNAVAILABLE_MESSAGE = "Neither the live API nor the cached fallback could produce this value.";

/**
 * Fetches from the live operational API first. Falls back to a verified
 * static presentation source ONLY on a genuine network failure (the live API
 * could not be reached at all). Never falls back on SCIENCE_INTEGRITY_FAILURE
 * (a hard scientific failure must never be masked by stale cached data) and
 * never falls back on a real "this product does not exist for this
 * year/case" answer (SCIENCE_PRODUCT_UNAVAILABLE / SCIENCE_CASE_NOT_ELIGIBLE)
 * -- those are correct, not failures, and are re-thrown so the caller can
 * show the real reason rather than a different product's cached value.
 */
export async function withStaticFallback<T>(
  liveFetch: () => Promise<T>,
  staticFetch: (() => Promise<T>) | null,
): Promise<DataSourceResult<T>> {
  try {
    const data = await liveFetch();
    return { mode: "VERIFIED_API", data, message: null };
  } catch (error) {
    // Fallback is only for a genuine network failure -- the live API could
    // not be reached at all. Anything else (INTEGRITY_FAILURE, a real
    // NOT_AVAILABLE/NOT_ELIGIBLE_FOR_CASE answer, or -- critically -- a
    // response that came back 200 OK but failed Zod schema validation, which
    // is a contract violation, not a network problem) must never be silently
    // masked by cached static data. Only the one recognized network-failure
    // case falls through to the static fetch below.
    if (error instanceof OperationalApiError) {
      if (error.kind === "INTEGRITY_FAILURE") {
        return { mode: "INTEGRITY_FAILURE", data: null, message: error.message };
      }
      if (error.kind !== "NETWORK_FAILURE") {
        // A real, correct unavailable/not-eligible answer -- surface it, don't fall back.
        throw error;
      }
    } else {
      // Not a recognized API error at all (e.g. a Zod ZodError from a
      // malformed/stale response body) -- treat as a hard integrity problem,
      // not a network failure, so it is never quietly masked by fallback data.
      return {
        mode: "INTEGRITY_FAILURE",
        data: null,
        message: error instanceof Error ? `Response failed contract validation: ${error.message}` : "Response failed contract validation.",
      };
    }
    if (!staticFetch) {
      return { mode: "NETWORK_FAILURE", data: null, message: error.message };
    }
    try {
      const data = await staticFetch();
      return { mode: "VERIFIED_STATIC_FALLBACK", data, message: FALLBACK_MESSAGE };
    } catch {
      return { mode: "UNAVAILABLE", data: null, message: UNAVAILABLE_MESSAGE };
    }
  }
}

export const DATA_SOURCE_LABEL: Record<DataSourceMode, string> = {
  VERIFIED_API: "Verified frozen API",
  VERIFIED_STATIC_FALLBACK: "Cached frozen presentation data",
  UNAVAILABLE: "Unavailable",
  INTEGRITY_FAILURE: "Integrity check failed",
  NETWORK_FAILURE: "API unreachable",
};
