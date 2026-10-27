import { describe, expect, it } from "vitest";
// @ts-expect-error -- plain ESM script without type declarations
import { THRESHOLDS, findFailures } from "../lighthouse-thresholds.mjs";

const report = (scores: Record<string, number | null>) => ({
  categories: Object.fromEntries(Object.entries(scores).map(([k, v]) => [k, { score: v }])),
});

const PASSING = { performance: 0.9, accessibility: 1, "best-practices": 0.95, seo: 1 };

describe("findFailures", () => {
  it("returns nothing when every category meets its threshold exactly", () => {
    expect(findFailures(report(PASSING))).toEqual([]);
  });

  it("names the category, the score and the minimum that failed", () => {
    expect(findFailures(report({ ...PASSING, accessibility: 0.98 }))).toEqual([
      "accessibility: 0.98 < 1",
    ]);
  });

  it("reports every failing category", () => {
    expect(findFailures(report({ ...PASSING, performance: 0.5, seo: 0.9 }))).toHaveLength(2);
  });

  it("treats a missing or null score as a failure", () => {
    const missing = findFailures({ categories: {} });
    const nulled = findFailures(report({ ...PASSING, seo: null }));

    expect(missing).toHaveLength(4);
    expect(nulled).toEqual(["seo: missing < 1"]);
  });

  it("requires accessibility and seo to be perfect", () => {
    expect(THRESHOLDS.accessibility).toBe(1);
    expect(THRESHOLDS.seo).toBe(1);
  });
});
