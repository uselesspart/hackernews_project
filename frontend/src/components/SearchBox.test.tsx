import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";

import { mockApi, renderRoute } from "../test/render";

describe("поиск", () => {
  beforeEach(() => {
    mockApi();
  });

  it("по фокусу показывает популярные технологии", async () => {
    const user = userEvent.setup();
    renderRoute("/");
    const input = screen.getByRole("combobox", { name: "Найти технологию" });
    await user.click(input);
    expect(await screen.findByText("Чаще всего в заголовках", { selector: "p" })).toBeInTheDocument();
    expect(input).toHaveAttribute("aria-expanded", "true");
    expect(screen.getAllByRole("option").length).toBeGreaterThan(3);
  });

  it("находит по синониму и объясняет совпадение", async () => {
    const user = userEvent.setup();
    renderRoute("/");
    await user.type(screen.getByRole("combobox"), "golang");
    const option = await screen.findByRole("option", { name: /^Go/ });
    expect(option).toHaveTextContent("по запросу «golang»");
    expect(option).toHaveTextContent("Язык программирования");
  });

  it("стрелки и Enter ведут на страницу технологии", async () => {
    const user = userEvent.setup();
    const { router } = renderRoute("/");
    const input = screen.getByRole("combobox");
    await user.type(input, "golang");
    await screen.findByRole("option", { name: /^Go/ });
    await user.keyboard("{ArrowDown}");
    expect(input.getAttribute("aria-activedescendant")).toBeTruthy();
    expect(screen.getByRole("option", { name: /^Go/ })).toHaveAttribute("aria-selected", "true");
    await user.keyboard("{Enter}");
    await waitFor(() => expect(router.state.location.pathname).toBe("/tech/go"));
  });

  it("сообщает, что технологию не отслеживаем, и закрывается по Esc", async () => {
    const user = userEvent.setup();
    renderRoute("/");
    const input = screen.getByRole("combobox");
    await user.type(input, "zzzz");
    expect(await screen.findByText(/«zzzz» мы не отслеживаем/)).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Ничего не найдено");
    await user.keyboard("{Escape}");
    expect(input).toHaveAttribute("aria-expanded", "false");
    await user.keyboard("{Escape}");
    expect(input).toHaveValue("");
  });

  it("клавиша / ставит фокус в поиск", async () => {
    const user = userEvent.setup();
    renderRoute("/");
    await user.keyboard("/");
    expect(screen.getByRole("combobox")).toHaveFocus();
  });
});
