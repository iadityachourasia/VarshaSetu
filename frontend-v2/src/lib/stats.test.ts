import { describe, expect, it } from "vitest";
import { median } from "./stats";

describe("median", () => {
  it("returns null for an empty sample", () => {
    expect(median([])).toBeNull();
  });

  it("returns the middle value for an odd-length sample", () => {
    expect(median([3, 1, 2])).toBe(2);
  });

  it("averages the two middle values for an even-length sample", () => {
    expect(median([1, 2, 3, 4])).toBe(2.5);
  });

  it("does not mutate the input array", () => {
    const values = [3, 1, 2];
    median(values);
    expect(values).toEqual([3, 1, 2]);
  });
});
