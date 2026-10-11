import { useState } from "react";

import { useMeta, useTechList } from "../api/queries";
import { BarList } from "../components/charts";
import { SearchBox } from "../components/SearchBox";
import { Button, ErrorState, Note, Section, Skeleton } from "../components/ui";
import { COMMENTS, countLabel, DAYS, endSentence, formatPeriod, spanDays, STORIES } from "../lib/format";
import { useDelayedFlag, useDocumentTitle } from "../lib/hooks";
import styles from "./HomePage.module.css";

const TOP_N = 10;
// Короче 4 недель динамика и тренды неинформативны (тот же порог, что у блока «Динамика»)
const SHORT_SPAN_DAYS = 28;

export function HomePage() {
  useDocumentTitle(null);
  return (
    <>
      <div className={styles.hero}>
        <h1 className={styles.title}>Как Hacker News говорит о технологиях</h1>
        <p className={styles.lead}>
          Найдите язык, базу данных, ИИ-модель или инструмент — покажем, сколько о нём пишут, с чем его
          связывают и каким тоном говорят в комментариях.
        </p>
        <div className={styles.search}>
          <SearchBox variant="hero" hotkey />
        </div>
        <DatasetLine />
      </div>
      <TopTechs />
    </>
  );
}

function DatasetLine() {
  const { data } = useMeta();
  if (!data) return <p className={styles.dataset}>&nbsp;</p>;
  const { stories, comments, period_start: start, period_end: end } = data;
  const days = start && end ? spanDays(start, end) : 0;
  return (
    <div className={styles.datasetWrap}>
      <p className={styles.dataset}>
        {endSentence(
          `В выборке ${countLabel(stories, STORIES)} и ${countLabel(comments, COMMENTS)}` +
            (start && end ? ` за ${formatPeriod(start, end)}` : ""),
        )}
      </p>
      {start && end && days < SHORT_SPAN_DAYS && (
        <Note tone="lowdata">
          Выборка пока короткая — {countLabel(Math.max(1, Math.round(days)), DAYS)}. Цифры предварительные: у
          большинства технологий мало статей, и мы помечаем такие оценки как ненадёжные.
        </Note>
      )}
    </div>
  );
}

function TopTechs() {
  const query = useTechList("stories", 1);
  const [all, setAll] = useState(false);
  const showSkeleton = useDelayedFlag(query.isPending);

  let body;
  if (query.isError) {
    body = (
      <ErrorState level={3} title="Не удалось загрузить список" onRetry={() => void query.refetch()}>
        <p>Сервер с данными не ответил. Проверьте соединение и попробуйте ещё раз.</p>
      </ErrorState>
    );
  } else if (query.isPending) {
    body = showSkeleton ? (
      <div className={styles.skeletons}>
        {Array.from({ length: TOP_N }, (_, i) => (
          <Skeleton key={i} height={28} />
        ))}
      </div>
    ) : null;
  } else if (query.data.length === 0) {
    body = <Note>Данных пока нет: пайплайн ещё не загрузил статьи. Поиск по каталогу технологий работает.</Note>;
  } else {
    const techs = all ? query.data : query.data.slice(0, TOP_N);
    body = (
      <>
        <BarList
          label="Технологии по числу статей"
          items={techs.map((t) => ({
            key: t.key,
            label: t.name,
            value: t.stories,
            to: `/tech/${t.key}`,
          }))}
        />
        {query.data.length > TOP_N && (
          <div>
            <Button onClick={() => setAll((v) => !v)}>
              {all ? "Свернуть" : `Показать все (${query.data.length})`}
            </Button>
          </div>
        )}
      </>
    );
  }

  return (
    <Section id="top" title="Чаще всего в заголовках" lead="Число статей, в заголовке которых упоминается технология.">
      {body}
    </Section>
  );
}
