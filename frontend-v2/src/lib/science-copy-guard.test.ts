import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { describe, expect, it } from "vitest";

// Phase 5A.3, section 70: guard against the public UI regressing into an
// overclaim. This scans rendered/renderable source text (not test files,
// not node_modules) for a set of forbidden phrases -- but a naive substring
// match would flag this app's own CORRECT usage everywhere, since the whole
// point of the product is to repeatedly say "NOT a live forecast", "NOT
// operationally proven", etc. So a match only fails the test when the
// phrase appears WITHOUT a negation word in the ~50 characters immediately
// before it. This is a heuristic, not a full parser -- it is meant to catch
// a new, unguarded positive claim slipping in, not to prove none exists.
const FORBIDDEN_PHRASES = [
  "live forecast", "operationally proven", "universal improvement", "true monsoon regime",
  "2025 untouched", "six-year climatology", "extreme-rain improvement overall", "combined 2019-2025 skill", "combined 2019–2025 skill",
];
const NEGATION_WINDOW = 50;
const NEGATION_PATTERN = /\b(not|no|never|isn't|isnt|without|neither|nor|not a|not an|non-)\b/i;

const SRC_ROOT = resolve(__dirname, "..");

function collectSourceFiles(dir: string, files: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    if (entry === "node_modules" || entry.startsWith(".")) continue;
    const full = join(dir, entry);
    const stats = statSync(full);
    if (stats.isDirectory()) collectSourceFiles(full, files);
    else if ((entry.endsWith(".tsx") || entry.endsWith(".ts")) && !entry.endsWith(".test.ts") && !entry.endsWith(".test.tsx")) files.push(full);
  }
  return files;
}

describe("science copy guard", () => {
  const files = collectSourceFiles(SRC_ROOT);
  it("found a nonzero number of source files to scan (sanity check the scan itself works)", () => {
    expect(files.length).toBeGreaterThan(50);
  });

  for (const phrase of FORBIDDEN_PHRASES) {
    it(`never states "${phrase}" without a nearby negation`, () => {
      const violations: string[] = [];
      for (const file of files) {
        const text = readFileSync(file, "utf8");
        const lowerText = text.toLowerCase();
        const lowerPhrase = phrase.toLowerCase();
        let searchFrom = 0;
        for (;;) {
          const index = lowerText.indexOf(lowerPhrase, searchFrom);
          if (index === -1) break;
          const windowStart = Math.max(0, index - NEGATION_WINDOW);
          const before = text.slice(windowStart, index);
          if (!NEGATION_PATTERN.test(before)) {
            violations.push(`${file.replace(SRC_ROOT, "src")}: ...${text.slice(windowStart, index + phrase.length + 20)}...`);
          }
          searchFrom = index + lowerPhrase.length;
        }
      }
      expect(violations, violations.join("\n")).toEqual([]);
    });
  }
});
