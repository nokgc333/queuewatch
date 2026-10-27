import { describe, expect, it } from "vitest";

import { STATUS_ORDER } from "@/domain/status/status";

import { ACTION_LABELS, ACTION_RESULT_LABELS, availableActions, JOB_ACTIONS } from "./actions";

describe("availableActions", () => {
  it.each([
    ["pending", ["pause", "cancel"]],
    ["retrying", ["pause", "cancel"]],
    ["paused", ["resume", "cancel"]],
    ["dead", ["requeue"]],
    ["cancelled", ["requeue"]],
    ["running", []],
    ["success", []],
  ] as const)("%s の操作は %j", (status, expected) => {
    expect(availableActions(status)).toEqual(expected);
  });

  it("全ての状態が、定義されている(未知の状態が増えたら、ここで気づく)", () => {
    for (const status of STATUS_ORDER) {
      expect(Array.isArray(availableActions(status))).toBe(true);
    }
  });

  it("全ての操作に、表示名と結果の文がある", () => {
    for (const action of JOB_ACTIONS) {
      expect(ACTION_LABELS[action]).toBeTruthy();
      expect(ACTION_RESULT_LABELS[action]).toBeTruthy();
    }
  });
});
