import { useId, useState } from "react";

import { STORIES_PAGE_SIZE, useTechStories } from "../../api/queries";
import type { StoryOut, StorySort } from "../../api/types";
import { ExternalIcon } from "../../components/icons";
import { Button, ErrorState, Section, Skeleton } from "../../components/ui";
import { COMMENTS, countLabel, formatShortDate, hostOf, plural, STORIES } from "../../lib/format";
import { useDelayedFlag } from "../../lib/hooks";
import styles from "./tech.module.css";

const SORTS: { value: StorySort; label: string }[] = [
  { value: "score", label: "По рейтингу" },
  { value: "comments", label: "По комментариям" },
  { value: "time", label: "Сначала новые" },
];

export function StoriesSection({ techKey, name, total }: { techKey: string; name: string; total: number }) {
  const [sort, setSort] = useState<StorySort>("score");
  const query = useTechStories(techKey, sort);
  const showSkeleton = useDelayedFlag(query.isPending);
  const groupName = useId();

  const items = query.data?.pages.flatMap((p) => p.items) ?? [];
  const loaded = items.length;
  const remaining = total - loaded;
  // Пока грузится новая сортировка, старый список остаётся на месте, приглушённым
  const refetchingSort = query.isPlaceholderData;

  return (
    <Section
      id="stories"
      title="Статьи"
      lead={`${countLabel(total, STORIES)} с ${name} в заголовке.`}
      aside={
        <fieldset className={styles.segmented}>
          <legend className="visually-hidden">Порядок статей</legend>
          {SORTS.map((s) => (
            <label key={s.value} className={styles.segment}>
              <input
                type="radio"
                name={groupName}
                value={s.value}
                checked={sort === s.value}
                onChange={() => setSort(s.value)}
              />
              <span>{s.label}</span>
            </label>
          ))}
        </fieldset>
      }
    >
      {query.isError && !query.data ? (
        <ErrorState level={3} title="Не удалось загрузить статьи" onRetry={() => void query.refetch()} />
      ) : query.isPending ? (
        showSkeleton ? (
          <div className={styles.storySkeleton}>
            {Array.from({ length: 5 }, (_, i) => (
              <Skeleton key={i} height={52} />
            ))}
          </div>
        ) : (
          <div className={styles.storySkeleton} />
        )
      ) : (
        <>
          <ol className={`${styles.stories} ${refetchingSort ? styles.busy : ""}`} aria-busy={refetchingSort}>
            {items.map((s) => (
              <li key={s.id}>
                <Story story={s} />
              </li>
            ))}
          </ol>
          {remaining > 0 && (
            <div>
              <Button onClick={() => void query.fetchNextPage()} disabled={query.isFetchingNextPage} busy={query.isFetchingNextPage}>
                {query.isFetchingNextPage ? "Загружаем…" : remaining <= STORIES_PAGE_SIZE ? `Показать ещё ${remaining}` : `Показать ещё ${STORIES_PAGE_SIZE} из ${remaining}`}
              </Button>
            </div>
          )}
          {query.isFetchNextPageError && <p className={styles.inlineError}>Не удалось загрузить следующие статьи.</p>}
        </>
      )}
    </Section>
  );
}

function Story({ story }: { story: StoryOut }) {
  const domain = story.domain ?? hostOf(story.url);
  const href = story.url ?? story.hn_url;
  return (
    <article className={styles.story}>
      <h3 className={styles.storyTitle}>
        <a href={href} rel="noopener noreferrer">
          {story.title ?? "Без заголовка"}
        </a>
        {domain && <span className={styles.domain}> ({domain})</span>}
      </h3>
      <p className={styles.storyMeta}>
        {story.score != null && (
          <span>
            {story.score} {plural(story.score, ["очко", "очка", "очков"])}
          </span>
        )}
        <a href={story.hn_url} rel="noopener noreferrer" className={styles.external}>
          {story.comments ? countLabel(story.comments, COMMENTS) : "обсуждение"} на HN
          <ExternalIcon className={styles.externalIcon} />
        </a>
        {story.time && <time dateTime={story.time}>{formatShortDate(story.time)}</time>}
      </p>
    </article>
  );
}
