import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { NewJobModal } from "../NewJobModal";

describe("NewJobModal", () => {
  it("入力した名前・優先度でonSubmitを呼ぶ", () => {
    const onSubmit = vi.fn();
    render(<NewJobModal onSubmit={onSubmit} onClose={vi.fn()} />);

    fireEvent.change(screen.getByPlaceholderText("SHOT010_render"), {
      target: { value: "SHOT099_render" },
    });
    fireEvent.change(screen.getByLabelText("優先度"), { target: { value: "high" } });
    fireEvent.click(screen.getByRole("button", { name: "登録" }));

    expect(onSubmit).toHaveBeenCalledWith({ name: "SHOT099_render", priority: "high" });
  });

  it("名前が空の場合はonSubmitを呼ばない", () => {
    const onSubmit = vi.fn();
    render(<NewJobModal onSubmit={onSubmit} onClose={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "登録" }));

    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("キャンセルボタンでonCloseを呼ぶ", () => {
    const onClose = vi.fn();
    render(<NewJobModal onSubmit={vi.fn()} onClose={onClose} />);

    fireEvent.click(screen.getByRole("button", { name: "キャンセル" }));

    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
