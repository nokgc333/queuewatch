import { readFileSync } from "node:fs";
import { findFailures } from "./lighthouse-thresholds.mjs";

const files = process.argv.slice(2);
let failed = false;
for (const file of files) {
  const report = JSON.parse(readFileSync(file, "utf-8"));
  const failures = findFailures(report);
  const scores = Object.entries(report.categories)
    .map(([name, value]) => `${name}=${Math.round(value.score * 100)}`)
    .join(" ");
  console.log(`${report.finalDisplayedUrl}: ${scores}`);
  for (const message of failures) {
    console.error(`  FAIL ${message}`);
    failed = true;
  }
}
process.exit(failed ? 1 : 0);
