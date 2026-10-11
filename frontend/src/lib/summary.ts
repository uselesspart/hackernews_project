import type { DatasetMeta, IrrBrief, TechProfile } from "../api/types";
import { countLabel, formatInt, formatShare, STORIES, timesLabel } from "./format";

/**
 * Вывод словами над цифрами: что запомнится, определяют заголовок и подпись,
 * а не сам график (Borkin и др. 2016). Ненадёжные метрики в вывод не попадают.
 */
export function buildLead(profile: TechProfile, meta: DatasetMeta | undefined): string[] {
  const { stats, sentiment, irr, name } = profile;
  if (stats.stories === 0) return [];

  const lead: string[] = [];
  const of = meta ? ` из ${formatInt(meta.stories)}` : "";
  lead.push(
    stats.rank
      ? `${stats.rank}-е место по числу статей: ${countLabel(stats.stories, STORIES)}${of} в выборке.`
      : `${countLabel(stats.stories, STORIES)}${of} в выборке.`,
  );

  if (sentiment.reliable && sentiment.pos_share != null && sentiment.neg_share != null) {
    const pos = formatShare(sentiment.pos_share);
    const neg = formatShare(sentiment.neg_share);
    if (sentiment.pos_share > sentiment.neg_share) {
      lead.push(`Позитивных комментариев больше, чем негативных: ${pos} против ${neg}.`);
    } else if (sentiment.pos_share < sentiment.neg_share) {
      lead.push(`Негативных комментариев больше, чем позитивных: ${neg} против ${pos}.`);
    } else {
      lead.push(`Позитивных и негативных комментариев поровну: по ${pos}.`);
    }
  } else if (sentiment.n > 0) {
    lead.push(`Для оценки тона пока мало комментариев: ${formatInt(sentiment.n)}.`);
  }

  const engagement = irrSentence(irr, name);
  if (engagement) lead.push(engagement);
  return lead;
}

export function irrSentence(irr: IrrBrief, name: string): string | null {
  if (!irr.reliable || irr.value == null) return null;
  if (!irr.significant) return `Заметной связи упоминания ${name} с числом комментариев не видно.`;
  return irr.value >= 1
    ? `Статьи с ${name} в заголовке собирают ${timesLabel(irr.value)} больше комментариев, чем статьи без отслеживаемых технологий.`
    : `Статьи с ${name} в заголовке собирают ${timesLabel(1 / irr.value)} меньше комментариев, чем статьи без отслеживаемых технологий.`;
}
