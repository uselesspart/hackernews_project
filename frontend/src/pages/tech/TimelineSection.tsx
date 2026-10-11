import { useTechTimeline } from "../../api/queries";
import type { DatasetMeta, TimelineBucket } from "../../api/types";
import { ColumnChart } from "../../components/charts";
import { ErrorState, Section, Skeleton } from "../../components/ui";
import { formatDayMonth, formatMonth, spanDays } from "../../lib/format";

// Меньше 4 недель — несколько точек, по которым тренд не читается (PLAN.md, 3.4)
export const MIN_TIMELINE_DAYS = 28;
// Дольше полугода недель слишком много для узкого экрана — переходим на месяцы
const WEEKLY_MAX_DAYS = 183;

export function TimelineSection({ techKey, meta }: { techKey: string; meta: DatasetMeta | undefined }) {
  const days = meta?.period_start && meta.period_end ? spanDays(meta.period_start, meta.period_end) : 0;
  const enabled = days >= MIN_TIMELINE_DAYS;
  const bucket: TimelineBucket = days > WEEKLY_MAX_DAYS ? "month" : "week";
  const query = useTechTimeline(techKey, bucket, enabled);

  if (!enabled) return null;
  return (
    <Section
      id="timeline"
      title="Динамика"
      lead={bucket === "week" ? "Число статей по неделям." : "Число статей по месяцам."}
    >
      {query.isError ? (
        <ErrorState level={3} title="Не удалось загрузить динамику" onRetry={() => void query.refetch()} />
      ) : !query.data ? (
        <Skeleton height={220} />
      ) : (
        <ColumnChart
          valueLabel="Статей"
          points={query.data.points.map((p) => ({
            key: p.period,
            label: bucket === "week" ? `неделя с ${formatDayMonth(p.period)}` : formatMonth(p.period),
            value: p.stories,
          }))}
        />
      )}
    </Section>
  );
}
