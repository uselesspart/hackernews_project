import { Link } from "react-router-dom";

import type { TechProfile } from "../../api/types";
import { BarList } from "../../components/charts";
import { Section } from "../../components/ui";
import { countLabel, STORIES } from "../../lib/format";
import styles from "./tech.module.css";

const SHOWN = 8;

/** Финал страницы: не тупик, а следующий шаг — переход к соседней технологии. */
export function RelatedSection({ profile }: { profile: TechProfile }) {
  const { cooccurring, neighbors, name } = profile;
  if (cooccurring.length === 0 && neighbors.length === 0) return null;

  return (
    <Section id="related" title={`Рядом с ${name}`}>
      <div className={styles.related}>
        {cooccurring.length > 0 && (
          <div>
            <h3 className={styles.subTitle}>Упоминают в одном заголовке</h3>
            <BarList
              label={`Технологии, упомянутые вместе с ${name}`}
              items={cooccurring.slice(0, SHOWN).map((t) => ({
                key: t.key,
                label: t.name,
                value: t.stories,
                valueText: countLabel(t.stories, STORIES),
                to: `/tech/${t.key}`,
              }))}
            />
          </div>
        )}
        {neighbors.length > 0 && (
          <div>
            <h3 className={styles.subTitle}>Обсуждают в похожем контексте</h3>
            <p className={styles.subLead}>По близости слов в комментариях (модель Word2Vec), от самых близких.</p>
            {/* Значения близости не показываем: на малом корпусе они почти одинаковы и создают ложную точность */}
            <ol className={styles.neighbors}>
              {neighbors.slice(0, SHOWN).map((t) => (
                <li key={t.key}>
                  <Link to={`/tech/${t.key}`}>{t.name}</Link>
                </li>
              ))}
            </ol>
          </div>
        )}
      </div>
    </Section>
  );
}
