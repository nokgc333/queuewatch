import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { JobFilters } from "../JobFilters";

describe("JobFilters", () => {
  it("検索の領域は、ランドマークと名前を持つ", () => {
    render(<JobFilters value={{ q: "", priority: "" }} onChange={() => undefined} />);

    expect(screen.getByRole("search", { name: "ジョブの検索" })).toBeInTheDocument();
  });

  it("名前を入力すると、q が変わる", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<JobFilters value={{ q: "", priority: "" }} onChange={onChange} />);

    await user.type(screen.getByLabelText("名前で検索"), "S");

    expect(onChange).toHaveBeenLastCalledWith({ q: "S", priority: "" });
  });

  it("優先度を選ぶと、priority が変わる", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<JobFilters value={{ q: "", priority: "" }} onChange={onChange} />);

    await user.selectOptions(screen.getByLabelText("優先度"), "high");

    expect(onChange).toHaveBeenCalledWith({ q: "", priority: "high" });
  });

  it("条件があるときだけ、クリアのボタンを出し、押すと空に戻す", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    const { rerender } = render(
      <JobFilters value={{ q: "", priority: "" }} onChange={onChange} />,
    );
    expect(screen.queryByRole("button", { name: "条件をクリア" })).not.toBeInTheDocument();

    rerender(<JobFilters value={{ q: "abc", priority: "low" }} onChange={onChange} />);
    await user.click(screen.getByRole("button", { name: "条件をクリア" }));

    expect(onChange).toHaveBeenCalledWith({ q: "", priority: "" });
  });

  it("Enter でフォームが送信(ページ遷移)されない", async () => {
    const user = userEvent.setup();
    render(<JobFilters value={{ q: "a", priority: "" }} onChange={() => undefined} />);

    await user.type(screen.getByLabelText("名前で検索"), "{Enter}");

    expect(window.location.pathname).toBe("/");
  });
});
