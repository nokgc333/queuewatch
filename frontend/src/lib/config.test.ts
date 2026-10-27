import { describe, expect, it } from "vitest";

import { resolveConfig } from "./config";

describe("resolveConfig", () => {
  it("何も無いときは、既定のAPIの場所を使い、トークンは無い", () => {
    expect(resolveConfig(undefined, {})).toEqual({
      apiBaseUrl: "http://localhost:8000",
      apiToken: undefined,
    });
  });

  it("ビルド時の環境変数を使う", () => {
    expect(resolveConfig(undefined, { VITE_API_BASE_URL: "https://a.test", VITE_API_TOKEN: "t" }))
      .toEqual({ apiBaseUrl: "https://a.test", apiToken: "t" });
  });

  it("実行時の設定は、ビルド時の環境変数より優先する", () => {
    expect(
      resolveConfig(
        { apiBaseUrl: "https://runtime.test", apiToken: "runtime-token" },
        { VITE_API_BASE_URL: "https://build.test", VITE_API_TOKEN: "build-token" },
      ),
    ).toEqual({ apiBaseUrl: "https://runtime.test", apiToken: "runtime-token" });
  });

  it("実行時の設定の空の値は、ビルド時の値へ戻る", () => {
    expect(
      resolveConfig({ apiBaseUrl: "", apiToken: "" }, { VITE_API_BASE_URL: "https://build.test" }),
    ).toEqual({ apiBaseUrl: "https://build.test", apiToken: undefined });
  });
});
