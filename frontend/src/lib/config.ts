/** フロントエンドからバックエンドAPIへの接続先設定（仕様書§11.5 env-vars）。 */

const DEFAULT_API_BASE_URL = "http://localhost:8000";

export interface RuntimeConfig {
  apiBaseUrl?: string;
  apiToken?: string;
}

declare global {
  interface Window {
    __QUEUEWATCH_CONFIG__?: RuntimeConfig;
  }
}

/**
 * 設定の優先順位: 実行時の設定(コンテナ起動時に /config.js が書く) > ビルド時の環境変数 > 既定値。
 * 実行時の設定があれば、同じイメージを、環境ごとに作り直さずに使える。
 */
export function resolveConfig(
  runtime: RuntimeConfig | undefined,
  env: { VITE_API_BASE_URL?: string; VITE_API_TOKEN?: string },
): { apiBaseUrl: string; apiToken: string | undefined } {
  return {
    apiBaseUrl: runtime?.apiBaseUrl || env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL,
    apiToken: runtime?.apiToken || env.VITE_API_TOKEN || undefined,
  };
}

function currentConfig(): { apiBaseUrl: string; apiToken: string | undefined } {
  return resolveConfig(
    typeof window === "undefined" ? undefined : window.__QUEUEWATCH_CONFIG__,
    import.meta.env,
  );
}

export const API_BASE_URL: string = currentConfig().apiBaseUrl;

/** 呼び出しのたびに読む(実行時の設定やテストでの差し替えに追従するため)。 */
export function getApiToken(): string | undefined {
  return currentConfig().apiToken;
}

/** SCR-001/SCR-002のポーリング間隔（ADR-0005、3秒固定）。 */
export const POLLING_INTERVAL_MS = 3000;
