/** domain/job/priority.ts の単体テスト（優先度表示ラベル・バッジ色、仕様書§6.2）。 */
import { describe, expect, it } from "vitest";

import { isValidPriority, PRIORITY_LABELS, PRIORITY_ORDER } from "./priority";

describe("isValidPriority", () => {
  it.each(PRIORITY_ORDER)("%sは有効な優先度と判定される", (priority) => {
    expect(isValidPriority(priority)).toBe(true);
  });

  it("未定義の優先度は無効", () => {
    expect(isValidPriority("urgent")).toBe(false);
  });
});

describe("PRIORITY_LABELS", () => {
  it("全優先度に日本語ラベルが定義されている", () => {
    for (const priority of PRIORITY_ORDER) {
      expect(PRIORITY_LABELS[priority]).toBeTruthy();
    }
  });
});
