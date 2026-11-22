import { useQueries } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";

import { getJson } from "../api/client";
import { useTechList } from "../api/queries";
import type { TechProfile } from "../api/types";
import { Note } from "../components/ui";
import { useDocumentTitle } from "../lib/hooks";
import styles from "./ExplorePage.module.css";

export function ComparePage() {
  useDocumentTitle("Сравнение технологий");
  const [params, setParams] = useSearchParams();
  const keys = [...new Set((params.get("keys") ?? "rust,python").split(",").filter(Boolean))].slice(0, 3);
  const list = useTechList().data ?? [];
  const queries = useQueries({ queries: keys.map((key) => ({
    queryKey: ["tech", key],
    queryFn: ({ signal }: { signal: AbortSignal }) => getJson<TechProfile>(`/techs/${encodeURIComponent(key)}`, {}, signal),
    staleTime: 10 * 60_000,
  })) });
  const change = (index: number, value: string) => {
    const next = [...keys]; next[index] = value;
    setParams({ keys: next.filter(Boolean).join(",") });
  };
  const profiles = queries.flatMap((q) => q.data ? [q.data] : []);
  const rows: [string, (p: TechProfile) => string][] = [
    ["Статей", (p) => String(p.stats.stories)],
    ["Доля всех статей", (p) => `${(100 * p.stats.share).toFixed(2)} %`],
    ["Комментариев в обсуждениях", (p) => String(p.stats.comments)],
    ["Общий тон", (p) => p.sentiment.reliable && p.sentiment.index != null ? p.sentiment.index.toFixed(2) : "Мало данных"],
    ["Тон о технологии", (p) => p.sentiment.aspect.reliable && p.sentiment.aspect.index != null
      ? p.sentiment.aspect.index.toFixed(2) : "Мало данных"],
    ["Вовлечённость IRR", (p) => p.irr.reliable && p.irr.value != null
      ? `×${p.irr.value.toFixed(2)} [${p.irr.low?.toFixed(2)}; ${p.irr.high?.toFixed(2)}]` : "Нет надёжной оценки"],
  ];
  return <article className={styles.page}>
    <h1>Сравнение технологий</h1>
    <p>Выберите две или три технологии. Все значения относятся к одной исторической выборке.</p>
    <div className={styles.choices}>{[0, 1, 2].map((i) => <label key={i}>
      Технология {i + 1}<select value={keys[i] ?? ""} onChange={(e) => change(i, e.target.value)}>
        <option value="">Не выбрана</option>
        {list.map((t) => <option key={t.key} value={t.key} disabled={keys.includes(t.key) && keys[i] !== t.key}>
          {t.name}</option>)}
      </select>
    </label>)}</div>
    {queries.some((q) => q.isError) && <Note>Не удалось загрузить одну из выбранных технологий.</Note>}
    {queries.some((q) => q.isPending) && <p>Загружаем сравнение…</p>}
    {profiles.length > 0 && <div className={styles.tableWrap}><table>
      <caption>Показатели выбранных технологий</caption>
      <thead><tr><th scope="col">Показатель</th>{profiles.map((p) =>
        <th scope="col" key={p.key}><Link to={`/tech/${p.key}`}>{p.name}</Link></th>)}</tr></thead>
      <tbody>{rows.map(([label, value]) => <tr key={label}><th scope="row">{label}</th>
        {profiles.map((p) => <td key={p.key}>{value(p)}</td>)}</tr>)}</tbody>
    </table></div>}
    <Note>Общий тон комментария и отношение к технологии — разные оценки. IRR показывает наблюдаемую
      связь с числом комментариев, а не причинный эффект. Интервалы 95 % относятся к отдельным оценкам.</Note>
  </article>;
}
