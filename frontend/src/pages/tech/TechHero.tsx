import { Link } from "react-router-dom";

import type { DatasetMeta, TechProfile } from "../../api/types";
import { ArrowLeftIcon } from "../../components/icons";
import { Chip, StatRow, StatTile } from "../../components/ui";
import { formatDecimal, formatInt, formatShare, formatShortDate } from "../../lib/format";
import { buildLead } from "../../lib/summary";
import styles from "./tech.module.css";

export function TechHero({ profile, meta }: { profile: TechProfile; meta: DatasetMeta | undefined }) {
  const { stats, name, aliases, categories, areas } = profile;
  const lead = buildLead(profile, meta);
  const hasVoices = profile.sentiment.positive.length > 0 || profile.sentiment.negative.length > 0;

  return (
    <header className={styles.hero}>
      <Link to="/" className={styles.back}>
        <ArrowLeftIcon className={styles.backIcon} />
        Все технологии
      </Link>
      <div className={styles.chips}>
        {[...categories, ...areas].map((c) => (
          <Chip key={c.key}>{c.name}</Chip>
        ))}
      </div>
      <h1 className={styles.name}>{name}</h1>
      {aliases.length > 0 && (
        <p className={styles.aliases}>
          <span className={styles.aliasesLabel}>Ищется также как:</span> {aliases.join(", ")}
        </p>
      )}

      {lead.length > 0 && (
        <p className={styles.lead}>
          {lead.join(" ")}
          {hasVoices && (
            <>
              {" "}
              <a href="#voices">Что именно пишут →</a>
            </>
          )}
        </p>
      )}

      {stats.stories > 0 && (
        <StatRow>
          <StatTile
            label="Статей"
            value={formatInt(stats.stories)}
            hint={stats.rank ? `${stats.rank}-е место по числу статей` : undefined}
          />
          <StatTile label="Комментариев к ним" value={formatInt(stats.comments)} />
          <StatTile
            label="Средний рейтинг статьи"
            value={stats.avg_score != null ? formatDecimal(stats.avg_score) : "—"}
            hint="очков на Hacker News"
          />
          <StatTile
            label="Доля всех статей"
            value={formatShare(stats.share)}
            hint={
              stats.first_story_at && stats.last_story_at
                ? `с ${formatShortDate(stats.first_story_at)} по ${formatShortDate(stats.last_story_at)}`
                : undefined
            }
          />
        </StatRow>
      )}
    </header>
  );
}
