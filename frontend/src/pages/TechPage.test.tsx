import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import rust from "../test/fixtures/profile-rust.json";
import { mockApi, renderRoute } from "../test/render";

describe("страница технологии", () => {
  it("богатые данные: вывод, числа, тон с голосами, статьи", async () => {
    mockApi();
    renderRoute("/tech/rust");
    expect(await screen.findByRole("heading", { level: 1, name: "Rust" })).toBeInTheDocument();
    expect(screen.getByText(/2-е место по числу статей: 14 статей из 161/)).toBeInTheDocument();
    expect(document.title).toBe("Rust — технологии на Hacker News");

    const sentiment = screen.getByRole("region", { name: "Тон комментариев" });
    expect(within(sentiment).getByText(/Индекс тона/)).toHaveTextContent("+0,24");
    expect(within(sentiment).getByRole("heading", { name: "Самые позитивные" })).toBeInTheDocument();
    expect(within(sentiment).getAllByRole("link", { name: /Весь комментарий на HN/ })).toHaveLength(6);

    const stories = screen.getByRole("region", { name: "Статьи" });
    // В выборке статья опубликована дважды — оба экземпляра остаются в списке
    expect(await within(stories).findAllByText(/Fivefold Slower Compared to Go/, { selector: "a" })).toHaveLength(2);
  });

  it("мало данных: не показывает индекс и IRR как результат", async () => {
    mockApi();
    renderRoute("/tech/rust");
    const engagement = await screen.findByRole("region", { name: "Вовлечённость" });
    // В фикстуре IRR есть, но reliable=false (14 статей): значение скрыто
    expect(within(engagement).getByText(/Мало статей для оценки: 14 статей/)).toBeInTheDocument();
    expect(within(engagement).queryByText(/×/)).toBeNull();
  });

  it("ненадёжный тон: пояснение вместо долей, цитаты остаются", async () => {
    const thin = { ...rust, sentiment: { ...rust.sentiment, reliable: false, n: 12 } };
    mockApi((url) => (url.pathname === "/api/techs/rust" ? { body: thin } : undefined));
    renderRoute("/tech/rust");
    const sentiment = await screen.findByRole("region", { name: "Тон комментариев" });
    expect(within(sentiment).getByText(/Мало данных для оценки тона: 12 комментариев/)).toBeInTheDocument();
    expect(within(sentiment).queryByText(/Индекс тона/)).toBeNull();
    expect(within(sentiment).getByRole("heading", { name: "Самые негативные" })).toBeInTheDocument();
  });

  it("технология без статей: объясняет и предлагает другие", async () => {
    mockApi();
    renderRoute("/tech/fossil");
    expect(await screen.findByRole("heading", { level: 1, name: "Fossil" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Статей пока нет" })).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Тон комментариев" })).toBeNull();
    expect(await screen.findByRole("link", { name: "JavaScript" })).toHaveAttribute("href", "/tech/javascript");
  });

  it("неизвестная технология — 404 с поиском", async () => {
    mockApi();
    renderRoute("/tech/nope");
    expect(
      await screen.findByRole("heading", { level: 1, name: "Такую технологию мы не отслеживаем" }),
    ).toBeInTheDocument();
    expect(screen.getAllByRole("combobox").length).toBeGreaterThan(0);
  });

  it("сбой сервера — сообщение и повтор", async () => {
    const fetchMock = mockApi((url) => (url.pathname === "/api/techs/rust" ? { status: 502, body: {} } : undefined));
    renderRoute("/tech/rust");
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Не удалось загрузить страницу");
    const before = fetchMock.mock.calls.length;
    await userEvent.setup().click(within(alert).getByRole("button", { name: "Повторить" }));
    expect(fetchMock.mock.calls.length).toBeGreaterThan(before);
  });
});
