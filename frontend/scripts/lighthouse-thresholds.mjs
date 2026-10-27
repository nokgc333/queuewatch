export const THRESHOLDS = {
  performance: 0.9,
  accessibility: 1,
  "best-practices": 0.95,
  seo: 1,
};

export function findFailures(report, thresholds = THRESHOLDS) {
  return Object.entries(thresholds)
    .map(([category, minimum]) => ({ category, minimum, score: report.categories[category]?.score }))
    .filter(({ score, minimum }) => score === undefined || score === null || score < minimum)
    .map(({ category, minimum, score }) => `${category}: ${score ?? "missing"} < ${minimum}`);
}
