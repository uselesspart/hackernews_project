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
    // Общий тон надёжен (54 комментария), тон о самом Rust — нет (13 реплик): доли только у общего
    expect(within(sentiment).getByText(/^Индекс тона\s*$/)).toHaveTextContent("+0,25");
    expect(within(sentiment).getByText(/Мало данных: 13 реплик о Rust/)).toBeInTheDocument();
    expect(within(sentiment).getByRole("heading", { name: "Самые позитивные о Rust" })).toBeInTheDocument();
    expect(within(sentiment).getAllByRole("link", { name: /Весь комментарий на HN/ })).toHaveLength(5);

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
    expect(within(sentiment).getByRole("heading", { name: "Самые негативные о Rust" })).toBeInTheDocument();
  });

  it("надёжный тон о технологии: две шкалы, о Rust — первой", async () => {
    const aspect = { index: -0.1, n: 40, reliable: true, pos_share: 0.2, neu_share: 0.4, neg_share: 0.4 };
    const rich = { ...rust, sentiment: { ...rust.sentiment, aspect } };
    mockApi((url) => (url.pathname === "/api/techs/rust" ? { body: rich } : undefined));
    renderRoute("/tech/rust");
    const sentiment = await screen.findByRole("region", { name: "Тон комментариев" });
    const indexes = within(sentiment).getAllByText(/^Индекс тона\s*$/);
    expect(indexes.map((el) => el.textContent)).toEqual(["Индекс тона -0,10", "Индекс тона +0,25"]);
    expect(within(sentiment).getByText(/из них Rust прямо называют в 40 комментариях/)).toBeInTheDocument();
    expect(screen.getByText(/Когда говорят о Rust, негативных реплик больше, чем позитивных: 40\s%/)).toBeInTheDocument();
  });

  it("примеры без упоминания технологии подписаны как «в обсуждениях»", async () => {
    const negative = rust.sentiment.negative.map((c) => ({ ...c, mentions: false }));
    const body = { ...rust, sentiment: { ...rust.sentiment, aspect: { ...rust.sentiment.aspect, n: 0 }, negative } };
    mockApi((url) => (url.pathname === "/api/techs/rust" ? { body } : undefined));
    renderRoute("/tech/rust");
    const sentiment = await screen.findByRole("region", { name: "Тон комментариев" });
    expect(within(sentiment).getByRole("heading", { name: "Самые негативные в обсуждениях" })).toBeInTheDocument();
    expect(within(sentiment).getByRole("heading", { name: "Самые позитивные о Rust" })).toBeInTheDocument();
    expect(within(sentiment).getByText(/Rust в этих комментариях прямо не называют/)).toBeInTheDocument();
    expect(within(sentiment).queryByText(/из них Rust прямо называют/)).toBeNull();
  });

  it("без соседей по модели финал ведёт к технологиям той же категории", async () => {
    // В фикстуре Rust нет ни общих заголовков, ни соседей: модель малого корпуса вырождена
    mockApi();
    renderRoute("/tech/rust");
    const related = await screen.findByRole("region", { name: "Рядом с Rust" });
    expect(within(related).getByRole("heading", { name: "Из той же категории" })).toBeInTheDocument();
    expect(await within(related).findByRole("link", { name: /^JavaScript/ })).toHaveAttribute("href", "/tech/javascript");
    expect(within(related).queryByRole("link", { name: /^Rust/ })).toBeNull();
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
