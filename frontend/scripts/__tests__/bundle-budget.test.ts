import { describe, expect, it } from "vitest";
// @ts-expect-error -- plain ESM script without type declarations
import { INITIAL_JS_GZIP_BUDGET, initialScripts } from "../bundle-budget.mjs";

describe("initialScripts", () => {
  it("index.html が直接読み込む JS だけを数える(遅延読み込みの分は含まない)", () => {
    const html =
      '<script type="module" crossorigin src="/assets/index-abc.js"></script>' +
      '<link rel="modulepreload" href="/assets/Stats-x.js">';

    expect(initialScripts(html)).toEqual(["/assets/index-abc.js"]);
  });

  it("assets の外の JS(設定ファイルなど)は数えない", () => {
    expect(initialScripts('<script src="/config.js"></script>')).toEqual([]);
  });

  it("予算は、元の 137.1 kB の半分以下", () => {
    expect(INITIAL_JS_GZIP_BUDGET).toBeLessThanOrEqual((137.1 / 2) * 1024);
  });
});
