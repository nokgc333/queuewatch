/** lib/polling.ts (usePolling) の単体テスト（仕様書ADR-0005、SCR-001の3秒間隔ポーリング）。 */
import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { usePolling } from "./polling";

describe("usePolling", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("マウント時に即座にfetcherを1回呼ぶ", async () => {
    const fetcher = vi.fn().mockResolvedValue("data-1");

    renderHook(() => usePolling(fetcher, 3000));

    await act(async () => {
      await Promise.resolve();
    });

    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  it("intervalMsごとに再度fetcherを呼ぶ", async () => {
    const fetcher = vi.fn().mockResolvedValue("data");

    renderHook(() => usePolling(fetcher, 3000));
    await act(async () => {
      await Promise.resolve();
    });

    await act(async () => {
      vi.advanceTimersByTime(3000);
      await Promise.resolve();
    });

    expect(fetcher).toHaveBeenCalledTimes(2);
  });

  it("成功時にdataを更新しerrorをnullにする", async () => {
    const fetcher = vi.fn().mockResolvedValue("hello");

    const { result } = renderHook(() => usePolling(fetcher, 3000));
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(result.current.data).toBe("hello");
    expect(result.current.error).toBeNull();
  });

  it("失敗時はerrorを設定しつつ直近のdataを保持する(仕様書§2.7フェイルセーフ)", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce("first")
      .mockRejectedValueOnce(new Error("network error"));

    const { result } = renderHook(() => usePolling(fetcher, 3000));
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(result.current.data).toBe("first");

    await act(async () => {
      vi.advanceTimersByTime(3000);
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(result.current.error).not.toBeNull();
    expect(result.current.data).toBe("first");
  });

  it("アンマウント後はfetcherの結果を反映しない", async () => {
    let resolveFetch: (value: string) => void = () => {};
    const fetcher = vi.fn().mockImplementation(
      () =>
        new Promise<string>((resolve) => {
          resolveFetch = resolve;
        }),
    );

    const { unmount } = renderHook(() => usePolling(fetcher, 3000));
    unmount();

    await act(async () => {
      resolveFetch("late-data");
      await Promise.resolve();
    });

    // アンマウント後にsetStateが呼ばれてもReactが警告を出さないことを期待する
    // (明示的なアサーションはなく、例外が発生しないことを確認するテスト)
    expect(fetcher).toHaveBeenCalledTimes(1);
  });
});
