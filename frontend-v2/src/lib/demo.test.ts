import { describe, expect, it } from "vitest";
import { defaultDemoCase, PRIMARY_DEMO_CASE_ID } from "./demo";
import type { CaseSummary } from "./api/science";

const stub = (case_id: string) => ({ case_id }) as CaseSummary;

describe("official video default", () => {
  it("uses the primary only when it is in the official catalogue", () => {
    expect(defaultDemoCase([stub(PRIMARY_DEMO_CASE_ID)], [stub(PRIMARY_DEMO_CASE_ID)])).toBe(PRIMARY_DEMO_CASE_ID);
    expect(defaultDemoCase([stub(PRIMARY_DEMO_CASE_ID)], [stub("official-other")])).toBe("official-other");
    expect(defaultDemoCase([stub("normal")], [])).toBe("normal");
  });
});
