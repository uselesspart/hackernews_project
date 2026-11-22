import { useTechForecast } from "../../api/queries";
import type { Forecast } from "../../api/types";
import { Note, Section } from "../../components/ui";

const percent = (value: number) => new Intl.NumberFormat("ru-RU", {
  style: "percent", minimumFractionDigits: 2, maximumFractionDigits: 2,
}).format(value);
const date = (value: string) => new Intl.DateTimeFormat("ru-RU", {
  day: "numeric", month: "long", year: "numeric", timeZone: "UTC",
}).format(new Date(value));

export function ForecastSection({ techKey }: { techKey: string }) {
  const query = useTechForecast(techKey);
  return (
    <Section id="forecast" title="Прогноз интереса" lead="Доля всех статей Hacker News, в заголовке которых упоминается технология.">
      {query.isError ? <Note>Не удалось загрузить прогноз.</Note> : query.isPending ?
        <Note>Загружаем прогноз…</Note> : <ForecastResult forecast={query.data} />}
    </Section>
  );
}

export function ForecastResult({ forecast: f }: { forecast: Forecast }) {
  if (f.status === "not_computed") return <Note>Прогноз ещё не рассчитан.</Note>;
  if (f.status !== "available" || f.share == null || !f.target_week || !f.data_through) {
    return <Note tone="lowdata">Для прогноза нужно не меньше 16 полных недель и 30 упоминаний в обучающей части. Сейчас недель: {f.weeks}, упоминаний за весь период: {f.mentions}.</Note>;
  }
  const archived = Date.parse(f.target_week) + 7 * 86400000 < Date.now();
  return (
    <div>
      {archived && <Note>Эксперимент на исторических данных. Эта оценка не описывает текущий интерес.</Note>}
      <p>На неделю с {date(f.target_week)}: <strong>{percent(f.share)}</strong> статей.
        {f.last_share != null && <> В последнюю полную неделю: {percent(f.last_share)}.</>}</p>
      <p>Данные по {date(f.data_through)}. Метод выбран на предыдущем временном отрезке.</p>
      {f.test_mae != null && f.baseline_mae != null && <p>
        Средняя ошибка на {f.test_weeks} следующих неделях: {(100 * f.test_mae).toFixed(3)} процентного пункта;
        у прогноза «как на прошлой неделе»: {(100 * f.baseline_mae).toFixed(3)}.
        {f.beats_baseline ? " На этом тесте ошибка меньше базовой." : " Преимущество перед базовым прогнозом на этом тесте не получено."}
      </p>}
      <Note>Экспериментальная точечная оценка. История короткая; доверительный интервал не рассчитан.</Note>
    </div>
  );
}
