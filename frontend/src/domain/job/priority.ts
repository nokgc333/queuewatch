/**
 * ジョブ優先度の表示ラベル純粋関数（バックエンドdomain/priority_queue.pyと対、仕様書§8.2）。
 */

export const PRIORITY_ORDER = ["high", "normal", "low"] as const;

export type Priority = (typeof PRIORITY_ORDER)[number];

export const PRIORITY_LABELS: Record<Priority, string> = {
  high: "高",
  normal: "中",
  low: "低",
};

export function isValidPriority(value: string): value is Priority {
  return (PRIORITY_ORDER as readonly string[]).includes(value);
}
