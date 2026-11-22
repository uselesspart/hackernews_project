import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ForecastResult } from "./ForecastSection";

describe("прогноз интереса", () => {
  it("показывает исторический период и отсутствие преимущества перед базовым прогнозом", () => {
    render(<ForecastResult forecast={{ status: "available", weeks: 16, mentions: 100,
      share: .01, last_share: .012, target_week: "2024-08-05", data_through: "2024-08-04",
      test_mae: .002, baseline_mae: .001, test_weeks: 4, beats_baseline: false, experimental: true }} />);
    expect(screen.getByText(/не описывает текущий интерес/)).toBeInTheDocument();
    expect(screen.getByText(/Преимущество перед базовым прогнозом.*не получено/)).toBeInTheDocument();
    expect(screen.getByText(/доверительный интервал не рассчитан/)).toBeInTheDocument();
  });
  it("объясняет нехватку истории без численного прогноза", () => {
    render(<ForecastResult forecast={{ status: "insufficient_data", weeks: 3, mentions: 9,
      test_weeks: 0, beats_baseline: false, experimental: true }} />);
    expect(screen.getByText(/не меньше 16 полных недель/)).toBeInTheDocument();
    expect(screen.queryByText(/На неделю с/)).toBeNull();
  });
  it("отличает отсутствие расчета от недостатка данных", () => {
    render(<ForecastResult forecast={{ status: "not_computed", weeks: 0, mentions: 0,
      test_weeks: 0, beats_baseline: false, experimental: true }} />);
    expect(screen.getByText("Прогноз ещё не рассчитан.")).toBeInTheDocument();
  });
});
