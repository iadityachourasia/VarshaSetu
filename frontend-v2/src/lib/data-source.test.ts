import { describe, expect, it } from "vitest";
import { z } from "zod";
import { OperationalApiError } from "./api/operational";
import { withStaticFallback } from "./data-source";

describe("withStaticFallback", () => {
  it("returns VERIFIED_API when the live fetch succeeds", async () => {
    const result = await withStaticFallback(async () => 42, async () => 0);
    expect(result).toEqual({ mode: "VERIFIED_API", data: 42, message: null });
  });

  it("falls back to static data only on a genuine NETWORK_FAILURE", async () => {
    const result = await withStaticFallback(
      async () => { throw new OperationalApiError("NETWORK_FAILURE", "Failed to fetch", null); },
      async () => 7,
    );
    expect(result.mode).toBe("VERIFIED_STATIC_FALLBACK");
    expect(result.data).toBe(7);
  });

  it("returns UNAVAILABLE when both the live fetch and the static fallback fail", async () => {
    const result = await withStaticFallback(
      async () => { throw new OperationalApiError("NETWORK_FAILURE", "Failed to fetch", null); },
      async () => { throw new Error("no cached artifact"); },
    );
    expect(result.mode).toBe("UNAVAILABLE");
    expect(result.data).toBeNull();
  });

  it("never falls back on SCIENCE_INTEGRITY_FAILURE, even when a static fallback exists", async () => {
    const result = await withStaticFallback(
      async () => { throw new OperationalApiError("INTEGRITY_FAILURE", "hash mismatch", 503, "SCIENCE_INTEGRITY_FAILURE"); },
      async () => 99,
    );
    expect(result.mode).toBe("INTEGRITY_FAILURE");
    expect(result.data).toBeNull();
  });

  it("re-throws a real NOT_AVAILABLE answer instead of masking it with fallback data", async () => {
    await expect(
      withStaticFallback(
        async () => { throw new OperationalApiError("NOT_AVAILABLE", "not available for 2023", 404, "SCIENCE_PRODUCT_UNAVAILABLE"); },
        async () => 1,
      ),
    ).rejects.toBeInstanceOf(OperationalApiError);
  });

  it("re-throws a real NOT_ELIGIBLE_FOR_CASE answer instead of masking it with fallback data", async () => {
    await expect(
      withStaticFallback(
        async () => { throw new OperationalApiError("NOT_ELIGIBLE_FOR_CASE", "QC failed", 404, "SCIENCE_CASE_NOT_ELIGIBLE"); },
        async () => 1,
      ),
    ).rejects.toBeInstanceOf(OperationalApiError);
  });

  it("regression: a Zod schema-validation failure on a 200 OK response is treated as an integrity problem, not silently masked by fallback data", async () => {
    // This is the exact bug found while migrating the Quality page: the live
    // endpoint returned 200 OK with a body from a stale server build (missing
    // newly-added fields). schema.parse() throws a plain ZodError, which is
    // NOT an OperationalApiError -- an earlier version of withStaticFallback
    // treated any non-OperationalApiError as network-failure-eligible and
    // silently served cached static data instead of surfacing the contract
    // violation. That must never happen again.
    const schema = z.object({ required_field: z.string() });
    const result = await withStaticFallback(
      async () => schema.parse({ wrong_shape: true }),
      async () => ({ required_field: "cached" }),
    );
    expect(result.mode).toBe("INTEGRITY_FAILURE");
    expect(result.data).toBeNull();
  });

  it("with no static fetch provided, a network failure surfaces as NETWORK_FAILURE", async () => {
    const result = await withStaticFallback(
      async () => { throw new OperationalApiError("NETWORK_FAILURE", "Failed to fetch", null); },
      null,
    );
    expect(result.mode).toBe("NETWORK_FAILURE");
  });
});
