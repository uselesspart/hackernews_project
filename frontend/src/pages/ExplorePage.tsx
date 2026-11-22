import { useState } from "react";
import { Link } from "react-router-dom";

import { useTechList } from "../api/queries";
import { Note } from "../components/ui";
import { useDocumentTitle } from "../lib/hooks";
import styles from "./ExplorePage.module.css";

export function ExplorePage() {
  useDocumentTitle("Карта и категории");
  const query = useTechList("stories", 1);
  const [category, setCategory] = useState("");
  if (query.isPending) return <p>Загружаем технологии…</p>;
  if (query.isError) return <Note>Не удалось загрузить технологии.</Note>;
  const categories = new Map(query.data.flatMap((t) => t.categories.map((c) => [c.key, c.name] as const)));
  const selected = query.data.filter((t) => !category || t.categories.some((c) => c.key === category));
  const mapped = selected.filter((t) => t.stories >= 30 && t.map_x != null && t.map_y != null);
  const xs = mapped.map((t) => t.map_x as number), ys = mapped.map((t) => t.map_y as number);
  const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys);
  const x = (value: number) => 40 + 720 * (value - minX) / (maxX - minX || 1);
  const y = (value: number) => 30 + 360 * (value - minY) / (maxY - minY || 1);
  const labels: { key: string; name: string; x: number; y: number; width: number; px: number; py: number }[] = [];
  for (const t of mapped.slice(0, 15)) {
    const px = x(t.map_x as number), py = y(t.map_y as number), width = t.name.length * 7;
    const offsets = [-9, 20, -29, 40, -49, 60, -69, 80];
    let placed = false;
    for (const dx of [10, -width - 10]) {
      for (const dy of offsets) {
        const lx = px + dx, ly = py + dy;
        if (lx < 8 || lx + width > 792 || ly < 16 || ly > 420) continue;
        if (labels.some((l) => lx < l.x + l.width + 5 && lx + width + 5 > l.x && Math.abs(ly - l.y) < 18)) continue;
        if (mapped.some((other) => {
          const ox = x(other.map_x as number), oy = y(other.map_y as number);
          return ox > lx - 7 && ox < lx + width + 7 && oy > ly - 18 && oy < ly + 7;
        })) continue;
        labels.push({ key: t.key, name: t.name, x: lx, y: ly, width, px, py });
        placed = true; break;
      }
      if (placed) break;
    }
  }
  return <article className={styles.page}>
    <h1>Карта и категории технологий</h1>
    <label>Категория <select value={category} onChange={(e) => setCategory(e.target.value)}>
      <option value="">Все категории</option>
      {[...categories].sort((a, b) => a[1].localeCompare(b[1], "ru")).map(([key, name]) =>
        <option key={key} value={key}>{name}</option>)}
    </select></label>
    <p>Карта показывает похожесть контекстов обсуждения по Word2Vec. Расстояния между далёкими
      группами t-SNE не измеряют степень связи. Показаны технологии минимум с 30 статьями.</p>
    {mapped.length ? <svg className={styles.map} viewBox="0 0 800 430" role="group" aria-label="Карта технологий">
      {mapped.map((t) => <a key={t.key} href={`/tech/${t.key}`} aria-label={`${t.name}: ${t.stories} статей`}>
        <circle cx={x(t.map_x as number)} cy={y(t.map_y as number)} r={6} />
        <title>{t.name}: {t.stories} статей</title>
      </a>)}
      {labels.map((l) => <g key={l.key} aria-hidden="true">
        <line x1={l.px} y1={l.py} x2={l.x} y2={l.y - 4} />
        <text x={l.x} y={l.y}>{l.name}</text>
      </g>)}
    </svg> : <Note>Для этой категории пока нет точек карты с достаточным числом статей.</Note>}
    <h2>Технологии категории</h2>
    <ul className={styles.catalog}>{selected.map((t) => <li key={t.key}>
      <Link to={`/tech/${t.key}`}>{t.name}</Link> — {t.stories} статей
    </li>)}</ul>
    <p><Link to="/compare">Сравнить технологии</Link></p>
  </article>;
}
