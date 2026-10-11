import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("найти технологию → открыть страницу → перейти к соседней", async ({ page }) => {
  await page.goto("/");
  const search = page.getByRole("combobox", { name: "Найти технологию" });
  await search.fill("rus");
  await page.getByRole("option", { name: /^Rust/ }).click();

  await expect(page).toHaveURL(/\/tech\/rust$/);
  await expect(page.getByRole("heading", { level: 1, name: "Rust" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Тон комментариев" })).toBeVisible();

  const related = page.getByRole("region", { name: "Рядом с Rust" });
  const neighbor = related.getByRole("link").first();
  const name = (await neighbor.textContent()) ?? "";
  await neighbor.click();
  await expect(page.getByRole("heading", { level: 1, name })).toBeVisible();
});

test("поиск с опечаткой и клавиатурой", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await page.keyboard.press("/");
  await page.keyboard.type("javscript");
  await expect(page.getByRole("option", { name: /^JavaScript/ })).toBeVisible();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/tech\/javascript$/);
});

for (const path of ["/", "/tech/rust", "/tech/fossil", "/tech/nope"]) {
  test(`axe без серьёзных нарушений: ${path}`, async ({ page }) => {
    await page.goto(path);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze();
    const serious = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
    expect(serious.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`)).toEqual([]);
  });
}

test("тёмная тема и открытый список подсказок без нарушений контраста", async ({ page }) => {
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto("/tech/rust");
  await page.getByRole("combobox").click();
  await expect(page.getByRole("listbox")).toBeVisible();
  const results = await new AxeBuilder({ page }).withTags(["wcag2aa"]).analyze();
  expect(results.violations.map((v) => v.id)).toEqual([]);
});
