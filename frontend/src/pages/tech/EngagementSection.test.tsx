import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { TechProfile } from "../../api/types";
import rust from "../../test/fixtures/profile-rust.json";
import { EngagementSection } from "./EngagementSection";

describe("состояния регрессии вовлечённости", () => {
  it.each([
    ["insufficient_data", "Мало статей для оценки: 14 статей"],
    ["model_failed", "модель не прошла проверку"],
    ["not_estimable", "не удалось получить корректную отдельную оценку"],
    ["not_computed", "ещё не рассчитана"],
  ] as const)("%s", (status, message) => {
    const profile = { ...rust, irr: { ...rust.irr, value: null, status, n: 14, reliable: false } };
    render(<EngagementSection profile={profile as TechProfile} />);
    expect(screen.getByText(new RegExp(message))).toBeInTheDocument();
    expect(screen.queryByText(/^×/)).toBeNull();
  });

  it("незначимая оценка показывает интервал без утверждения о росте", () => {
    const profile = { ...rust, irr: { value: 1.1, low: .8, high: 1.5, pval: .5, n: 100,
      status: "available", reliable: true, significant: false } };
    render(<EngagementSection profile={profile as TechProfile} />);
    expect(screen.getByText(/интервал включает 1/)).toBeInTheDocument();
    expect(screen.getByText(/95 % интервал:/)).toBeInTheDocument();
    expect(screen.queryByText(/большее ожидаемое/)).toBeNull();
  });
});
