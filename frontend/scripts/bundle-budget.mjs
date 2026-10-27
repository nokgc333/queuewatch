import { readFileSync } from "node:fs";
import { gzipSync } from "node:zlib";
import { join } from "node:path";

/** 起動時に読み込む JS(index.html が直接参照するもの)の gzip の合計の上限(バイト)。元は 137.1 kB。 */
export const INITIAL_JS_GZIP_BUDGET = 68 * 1024;

export function initialScripts(html) {
  return [...html.matchAll(/<script[^>]*\ssrc="([^"]+\.js)"/g)]
    .map((m) => m[1])
    .filter((src) => src.startsWith("/assets/"));
}

export function measure(distDir) {
  const html = readFileSync(join(distDir, "index.html"), "utf-8");
  return initialScripts(html).reduce(
    (total, src) => total + gzipSync(readFileSync(join(distDir, src))).length,
    0,
  );
}

if (process.argv[1] && process.argv[1].endsWith("bundle-budget.mjs")) {
  const size = measure(process.argv[2] ?? "dist");
  const kb = (size / 1024).toFixed(1);
  console.log(`initial JS (gzip): ${kb} kB (budget ${INITIAL_JS_GZIP_BUDGET / 1024} kB)`);
  process.exit(size <= INITIAL_JS_GZIP_BUDGET ? 0 : 1);
}
