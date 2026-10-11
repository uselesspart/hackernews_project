import { Link, useParams } from "react-router-dom";

import { isNotFound } from "../api/client";
import { useMeta, useTechProfile } from "../api/queries";
import type { DatasetMeta, TechProfile } from "../api/types";
import { SearchBox } from "../components/SearchBox";
import { ErrorState, Skeleton } from "../components/ui";
import { useDelayedFlag, useDocumentTitle } from "../lib/hooks";
import { DomainsSection, WordsSection } from "./tech/DiscussionSections";
import { EngagementSection } from "./tech/EngagementSection";
import { MethodNote } from "./tech/MethodNote";
import { NoStories } from "./tech/NoStories";
import { RelatedSection } from "./tech/RelatedSection";
import { SentimentSection } from "./tech/SentimentSection";
import { StoriesSection } from "./tech/StoriesSection";
import { TechHero } from "./tech/TechHero";
import { TimelineSection } from "./tech/TimelineSection";
import styles from "./TechPage.module.css";

export function TechPage() {
  const key = (useParams().key ?? "").toLowerCase();
  const profile = useTechProfile(key);
  const meta = useMeta().data;
  const showSkeleton = useDelayedFlag(profile.isPending);
  useDocumentTitle(profile.data?.name ?? (isNotFound(profile.error) ? "Не найдено" : null));

  if (profile.isError) {
    if (isNotFound(profile.error)) return <UnknownTech query={key} />;
    return (
      <ErrorState level={1} title="Не удалось загрузить страницу" onRetry={() => void profile.refetch()}>
        <p>Сервер с данными не ответил. Проверьте соединение и попробуйте ещё раз.</p>
      </ErrorState>
    );
  }
  if (profile.isPending) return showSkeleton ? <TechSkeleton /> : null;
  return <TechView profile={profile.data} meta={meta} />;
}

function TechView({ profile, meta }: { profile: TechProfile; meta: DatasetMeta | undefined }) {
  const hasStories = profile.stats.stories > 0;
  return (
    <article className={styles.page}>
      <TechHero profile={profile} meta={meta} />
      {hasStories ? (
        <>
          <PageNav profile={profile} />
          <SentimentSection profile={profile} />
          <StoriesSection techKey={profile.key} name={profile.name} total={profile.stats.stories} />
          <EngagementSection profile={profile} />
          <div className={styles.pair}>
            <WordsSection words={profile.words} />
            <DomainsSection domains={profile.domains} />
          </div>
          <TimelineSection techKey={profile.key} meta={meta} />
          <RelatedSection profile={profile} />
          <MethodNote meta={meta} />
        </>
      ) : (
        <NoStories profile={profile} meta={meta} />
      )}
    </article>
  );
}

function PageNav({ profile }: { profile: TechProfile }) {
  const links = [
    ["sentiment", "Тон комментариев"],
    ["stories", "Статьи"],
    ["engagement", "Вовлечённость"],
    ...(profile.words.length ? [["words", "О чём говорят"]] : []),
    ...(profile.cooccurring.length || profile.neighbors.length ? [["related", "Рядом"]] : []),
  ] as const;
  return (
    <nav aria-label="Разделы страницы" className={styles.nav}>
      <ul>
        {links.map(([id, label]) => (
          <li key={id}>
            <a href={`#${id}`}>{label}</a>
          </li>
        ))}
      </ul>
    </nav>
  );
}

function UnknownTech({ query }: { query: string }) {
  return (
    <div className={styles.unknown}>
      <h1>Такую технологию мы не отслеживаем</h1>
      <p>
        Страницы «{query}» нет: в каталоге только технологии, которые мы умеем находить в заголовках статей.
        Попробуйте поиск — он знает синонимы и терпит опечатки.
      </p>
      <SearchBox variant="hero" hotkey />
      <p>
        <Link to="/">Все отслеживаемые технологии</Link>
      </p>
    </div>
  );
}

function TechSkeleton() {
  return (
    <div className={styles.skeleton} aria-busy="true" aria-label="Загрузка">
      <Skeleton width={180} height={20} />
      <Skeleton width="40%" height={56} />
      <Skeleton width="70%" height={22} />
      <div className={styles.skeletonStats}>
        {Array.from({ length: 4 }, (_, i) => (
          <Skeleton key={i} height={96} />
        ))}
      </div>
      <Skeleton height={200} />
    </div>
  );
}
