import type { TechProfile } from "../../api/types";
import { Note, Section } from "../../components/ui";
import { countLabel, formatDecimal, STORIES } from "../../lib/format";
import { irrSentence } from "../../lib/summary";
import styles from "./tech.module.css";

export function EngagementSection({ profile }: { profile: TechProfile }) {
  const { irr, name, stats } = profile;
  const sentence = irrSentence(irr, name);

  return (
    <Section
      id="engagement"
      title="Вовлечённость"
      lead="Как упоминание технологии в заголовке связано с ожидаемым числом комментариев с учётом других технологий и формата статьи. Связь не означает причину."
    >
      {sentence && irr.value != null ? (
        <div className={styles.irr}>
          <p className={styles.irrFigure}>
            <span className={styles.irrValue}>×{formatDecimal(irr.value)}</span>
            {irr.low != null && irr.high != null && (
              <span className={styles.irrInterval}>
                95 % интервал: {formatDecimal(irr.low)}–{formatDecimal(irr.high)}
              </span>
            )}
          </p>
          <p className={styles.irrText}>{sentence}</p>
          {irr.significant_adjusted != null && <p>
            {irr.significant_adjusted
              ? "Связь сохраняет статистическую значимость после поправки Бенджамини — Хохберга на множество технологий (FDR 5%)."
              : "После поправки Бенджамини — Хохберга на множество технологий статистическая значимость не подтверждена (FDR 5%)."}
            {" "}95 % интервал выше относится к отдельной оценке.
          </p>}
        </div>
      ) : irr.status === "insufficient_data" || (irr.value != null && !irr.status) ? (
        <Note tone="lowdata">
          Мало статей для оценки: {countLabel(irr.n ?? stats.stories, STORIES)}. Значение не показываем.
        </Note>
      ) : irr.status === "model_failed" ? (
        <Note>Оценка вовлечённости временно недоступна: модель не прошла проверку. Число статей: {irr.n ?? stats.stories}.</Note>
      ) : irr.status === "not_estimable" ? (
        <Note>Для {name} не удалось получить корректную отдельную оценку. Число статей: {irr.n ?? stats.stories}.</Note>
      ) : (
        <Note>Оценка вовлечённости ещё не рассчитана.</Note>
      )}
    </Section>
  );
}
