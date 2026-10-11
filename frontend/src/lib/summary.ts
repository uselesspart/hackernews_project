import type { DatasetMeta, IrrBrief, Sentiment, TechProfile } from "../api/types";
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

  const tone = toneSentence(sentiment, name);
  if (tone) lead.push(tone);

  const engagement = irrSentence(irr, name);
  if (engagement) lead.push(engagement);
  return lead;
}

/**
 * Тон о самой технологии отвечает на вопрос страницы точнее, чем тон всего обсуждения,
 * поэтому он в приоритете; в формулировке всегда сказано, о чём именно доли.
 */
export function toneSentence(sentiment: Sentiment, name: string): string | null {
  const { aspect } = sentiment;
  if (aspect.reliable && aspect.pos_share != null && aspect.neg_share != null) {
    return compareShares(aspect.pos_share, aspect.neg_share, `Когда говорят о ${name},`, "реплик");
  }
  if (sentiment.reliable && sentiment.pos_share != null && sentiment.neg_share != null) {
    return compareShares(sentiment.pos_share, sentiment.neg_share, `В обсуждениях статей о ${name}`, "комментариев");
  }
  if (sentiment.n > 0) return `Для оценки тона пока мало комментариев: ${formatInt(sentiment.n)}.`;
  return null;
}

function compareShares(pos: number, neg: number, scope: string, unit: string): string {
  const p = formatShare(pos);
  const n = formatShare(neg);
  if (pos > neg) return `${scope} позитивных ${unit} больше, чем негативных: ${p} против ${n}.`;
  if (pos < neg) return `${scope} негативных ${unit} больше, чем позитивных: ${n} против ${p}.`;
  return `${scope} позитивных и негативных ${unit} поровну: по ${p}.`;
}

export function irrSentence(irr: IrrBrief, name: string): string | null {
  if (!irr.reliable || irr.value == null) return null;
  if (!irr.significant) return `Заметной связи упоминания ${name} с числом комментариев не видно.`;
  return irr.value >= 1
    ? `Статьи с ${name} в заголовке собирают ${timesLabel(irr.value)} больше комментариев, чем статьи без отслеживаемых технологий.`
    : `Статьи с ${name} в заголовке собирают ${timesLabel(1 / irr.value)} меньше комментариев, чем статьи без отслеживаемых технологий.`;
}
