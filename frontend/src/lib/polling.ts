/**
 * 定期ポーリングフック(usePolling)（仕様書ADR-0005: WebSocketではなくポーリング採用）。
 *
 * SCR-001/SCR-002で3秒間隔のポーリングに使う。失敗時は直近の表示を保持しつつ
 * エラー状態のみ更新する（仕様書§2.7の「フェイルセーフのUI挙動」）。
 */
import { useEffect, useRef, useState } from "react";

export interface PollingState<T> {
  data: T | null;
  error: Error | null;
  isLoading: boolean;
}

export function usePolling<T>(
  fetcher: () => Promise<T>,
  intervalMs: number,
): PollingState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  useEffect(() => {
    let isMounted = true;

    const run = async (): Promise<void> => {
      try {
        const result = await fetcherRef.current();
        if (!isMounted) return;
        setData(result);
        setError(null);
      } catch (err) {
        if (!isMounted) return;
        setError(err instanceof Error ? err : new Error(String(err)));
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };

    void run();
    const timer = setInterval(() => {
      void run();
    }, intervalMs);

    return () => {
      isMounted = false;
      clearInterval(timer);
    };
  }, [intervalMs]);

  return { data, error, isLoading };
}
