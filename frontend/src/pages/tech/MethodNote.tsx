import type { DatasetMeta } from "../../api/types";
import { countLabel, DAYS, formatPeriod, spanDays } from "../../lib/format";
import styles from "./tech.module.css";
import { MIN_TIMELINE_DAYS } from "./TimelineSection";

export function MethodNote({ meta }: { meta: DatasetMeta | undefined }) {
  const days = meta?.period_start && meta.period_end ? spanDays(meta.period_start, meta.period_end) : null;
  return (
    <details className={styles.method}>
      <summary>Откуда эти цифры</summary>
      <div className={styles.methodBody}>
        {meta?.period_start && meta.period_end && (
          <p>
            Выборка: статьи и комментарии Hacker News за {formatPeriod(meta.period_start, meta.period_end)}.
            {days != null && days < MIN_TIMELINE_DAYS &&
              ` Динамику по неделям покажем, когда выборка охватит от 4 недель (сейчас ${countLabel(Math.max(1, Math.round(days)), DAYS)}).`}
          </p>
        )}
        <p>
          <strong>Статьи о технологии</strong> — те, в заголовке которых она упомянута. Распознавание идёт по шаблонам
          названий и синонимов, поэтому возможны ложные совпадения (например, rust — не только язык).
        </p>
        <p>
          <strong>Тон</strong> оценивается словарным методом VADER по всем комментариям к статьям о технологии.
          Цитаты чужих реплик (строки с «&gt;») и код не учитываются. «Когда говорят о технологии» — только
          предложения, где она названа; «всё обсуждение» — комментарии целиком. Сарказм метод не различает, а в
          предложении о двух технологиях тон засчитывается обеим.
        </p>
        <p>
          <strong>Вовлечённость</strong> — отношение ожидаемого числа комментариев (регрессия отрицательного
          биномиального распределения) для статей с технологией в заголовке к статьям без отслеживаемых технологий.
        </p>
        <p>
          <strong>Похожий контекст</strong> — ближайшие технологии в модели Word2Vec, обученной на текстах обсуждений.
        </p>
        <p>Оценки на малом числе статей или комментариев мы помечаем как ненадёжные и не выносим в выводы.</p>
      </div>
    </details>
  );
}
