/** フロントエンドからバックエンドAPIへの接続先設定（仕様書§11.5 env-vars）。 */

export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

/** SCR-001/SCR-002のポーリング間隔（ADR-0005、3秒固定）。 */
export const POLLING_INTERVAL_MS = 3000;
