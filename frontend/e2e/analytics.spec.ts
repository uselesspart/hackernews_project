import { expect, test } from "@playwright/test";

test("архивный прогноз показывает период и сравнение с базовым методом", async ({ page }) => {
  await page.goto("/tech/rust");
  const forecast = page.getByRole("region", { name: "Прогноз интереса" });
  await expect(forecast).toContainText("не описывает текущий интерес");
  await expect(forecast).toContainText("2024");
  await expect(forecast).toContainText("как на прошлой неделе");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
});

test("карта фильтрует категорию и ведёт на страницу технологии", async ({ page }) => {
  await page.goto("/explore");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Карта и категории технологий");
  await page.getByLabel("Категория").selectOption("programming_language");
  const map = page.getByRole("group", { name: "Карта технологий" });
  await expect(map.getByRole("link", { name: /^Rust:/ })).toBeVisible();
  await map.getByRole("link", { name: /^Rust:/ }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Rust" })).toBeVisible();
});

test("сравнение показывает данные двух технологий", async ({ page }) => {
  await page.goto("/compare?keys=rust,python");
  const table = page.getByRole("table", { name: "Показатели выбранных технологий" });
  await expect(table.getByRole("columnheader", { name: "Rust" })).toBeVisible();
  await expect(table.getByRole("columnheader", { name: "Python" })).toBeVisible();
  await expect(table.getByRole("rowheader", { name: "Вовлечённость IRR" })).toBeVisible();
});
