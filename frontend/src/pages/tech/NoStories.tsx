import { Link } from "react-router-dom";

import { useTechList } from "../../api/queries";
import type { DatasetMeta, TechProfile } from "../../api/types";
import { Note, Section } from "../../components/ui";
import { formatPeriod } from "../../lib/format";
import styles from "./tech.module.css";

/** Технология в каталоге есть, а статей в выборке нет: объясняем почему и даём следующий шаг. */
export function NoStories({ profile, meta }: { profile: TechProfile; meta: DatasetMeta | undefined }) {
  const popular = useTechList("stories", 1).data?.slice(0, 8) ?? [];
  const period = meta?.period_start && meta.period_end ? ` за ${formatPeriod(meta.period_start, meta.period_end)}` : "";

  return (
    <Section id="empty" title="Статей пока нет">
      <Note>
        Мы отслеживаем {profile.name}, но{period} в заголовках статей нет ни одного упоминания. Страница заполнится,
        когда такие статьи появятся в выборке.
      </Note>
      {popular.length > 0 && (
        <div>
          <h3 className={styles.subTitle}>Чаще всего в заголовках сейчас</h3>
          <ul className={styles.inlineLinks}>
            {popular.map((t) => (
              <li key={t.key}>
                <Link to={`/tech/${t.key}`}>{t.name}</Link>
              </li>
            ))}
          </ul>
        </div>
      )}
    </Section>
  );
}
