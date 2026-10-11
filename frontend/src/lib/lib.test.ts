import { describe, expect, it } from "vitest";

import type { TechProfile } from "../api/types";
import { niceTicks } from "../components/charts";
import fossil from "../test/fixtures/profile-fossil.json";
import rust from "../test/fixtures/profile-rust.json";
import meta from "../test/fixtures/meta.json";
import { endSentence, formatPeriod, formatShare, plural, STORIES, timesLabel } from "./format";
import { buildLead, irrSentence } from "./summary";

const rustProfile = rust as TechProfile;

describe("format", () => {
  it("склоняет по-русски", () => {
    expect([1, 2, 5, 11, 21, 22, 25].map((n) => plural(n, STORIES))).toEqual([
      "статья",
      "статьи",
      "статей",
      "статей",
      "статья",
      "статьи",
      "статей",
    ]);
  });

  it("пишет «в N раз(а)»", () => {
    expect(timesLabel(1.84)).toBe("в 1,8 раза");
    expect(timesLabel(3)).toBe("в 3 раза");
    expect(timesLabel(5.02)).toBe("в 5 раз");
  });

  it("малые доли не превращаются в 0 %", () => {
    expect(formatShare(0.004).replace(/\s/g, " ")).toBe("0,4 %");
    expect(formatShare(0.593).replace(/\s/g, " ")).toBe("59 %");
  });

  it("период и конец предложения без двойной точки", () => {
    const period = formatPeriod("2024-04-11T09:12:24", "2024-04-13T02:34:18");
    expect(period).toMatch(/^11.13 апреля 2024/);
    expect(endSentence(`за ${period}`).endsWith("..")).toBe(false);
    expect(endSentence("готово")).toBe("готово.");
  });

  it("деления оси целые и покрывают максимум", () => {
    expect(niceTicks(1)).toEqual([0, 1]);
    expect(niceTicks(19)).toEqual([0, 10, 20]);
    expect(niceTicks(7)).toEqual([0, 5, 10]);
  });
});

describe("buildLead", () => {
  it("выносит в вывод место и надёжный тон, но не ненадёжный IRR", () => {
    const lead = buildLead(rustProfile, meta).join(" ");
    expect(lead).toContain("2-е место по числу статей: 14 статей из 161");
    expect(lead).toMatch(/Позитивных комментариев больше, чем негативных: 59\s%/);
    expect(lead).not.toMatch(/комментариев собирают/);
  });

  it("не пишет вывод о тоне при малой выборке", () => {
    const thin = { ...rustProfile, sentiment: { ...rustProfile.sentiment, reliable: false, n: 8 } };
    const lead = buildLead(thin, meta).join(" ");
    expect(lead).toContain("Для оценки тона пока мало комментариев: 8.");
    expect(lead).not.toMatch(/Позитивных/);
  });

  it("пустой вывод для технологии без статей", () => {
    expect(buildLead(fossil as TechProfile, meta)).toEqual([]);
  });

  it("IRR: больше, меньше, незначимо", () => {
    const base = { low: 1.2, high: 2.6, pval: 0.01, reliable: true, significant: true };
    expect(irrSentence({ ...base, value: 1.84 }, "Rust")).toBe(
      "Статьи с Rust в заголовке собирают в 1,8 раза больше комментариев, чем статьи без отслеживаемых технологий.",
    );
    expect(irrSentence({ ...base, value: 0.5 }, "Rust")).toContain("в 2 раза меньше");
    expect(irrSentence({ ...base, value: 1.1, significant: false }, "Rust")).toContain("Заметной связи");
    expect(irrSentence({ ...base, value: 1.84, reliable: false }, "Rust")).toBeNull();
  });
});
