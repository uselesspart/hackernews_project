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
      lead="Во сколько раз больше или меньше комментариев собирают статьи с технологией в заголовке — по сравнению со статьями без отслеживаемых технологий."
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
        </div>
      ) : irr.value == null ? (
        <Note>Для {name} оценки нет: технология слишком редко встречается в заголовках, чтобы включить её в модель.</Note>
      ) : (
        <Note tone="lowdata">
          Мало статей для оценки: {countLabel(stats.stories, STORIES)}. На такой выборке модель даёт слишком широкий
          интервал, поэтому значение не показываем.
        </Note>
      )}
    </Section>
  );
}
