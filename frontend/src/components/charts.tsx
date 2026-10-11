import { useState, type ReactNode } from "react";
import { Link } from "react-router-dom";

import { formatInt, formatShare } from "../lib/format";
import styles from "./charts.module.css";

export interface BarItem {
  key: string;
  label: ReactNode;
  value: number;
  /** Подпись значения у конца полосы; по умолчанию — само число */
  valueText?: string;
  /** Внутренняя ссылка (страница технологии) */
  to?: string;
  /** Внешняя ссылка */
  href?: string;
}

/**
 * Рейтинг полосами: одна серия — один цвет, значение у конца полосы.
 * Сами значения — текст в строке, поэтому отдельная «табличная» версия не нужна.
 */
export function BarList({ items, label }: { items: BarItem[]; label: string }) {
  const max = Math.max(...items.map((i) => i.value), 0);
  return (
    <ol className={styles.barList} aria-label={label}>
      {items.map((item) => {
        const pct = max > 0 ? (item.value / max) * 100 : 0;
        const text = item.valueText ?? formatInt(item.value);
        return (
          <li key={item.key} className={styles.barRow}>
            <span className={styles.barLabel}>
              {item.to ? (
                <Link to={item.to}>{item.label}</Link>
              ) : item.href ? (
                <a href={item.href} rel="noopener noreferrer">
                  {item.label}
                </a>
              ) : (
                item.label
              )}
            </span>
            <span className={styles.barTrack} aria-hidden="true">
              <span className={styles.bar} style={{ width: item.value > 0 ? `max(${pct}%, 3px)` : 0 }} />
            </span>
            <span className={`${styles.barValue} tabular`}>{text}</span>
          </li>
        );
      })}
    </ol>
  );
}

/**
 * Доли тональности: негативные | нейтральные | позитивные. Шкала упорядоченная,
 * поэтому дивергентная пара (красный ↔ синий) с серой серединой; значения подписаны
 * в легенде текстом — цвет не единственный носитель смысла.
 */
export function SentimentBar({ pos, neu, neg }: { pos: number; neu: number; neg: number }) {
  const parts = [
    { key: "neg", label: "негативные", share: neg, className: styles.neg },
    { key: "neu", label: "нейтральные", share: neu, className: styles.neu },
    { key: "pos", label: "позитивные", share: pos, className: styles.pos },
  ];
  return (
    <figure className={styles.sentiment}>
      <div className={styles.sentimentBar} aria-hidden="true">
        {parts
          .filter((p) => p.share > 0)
          .map((p) => (
            <span
              key={p.key}
              className={`${styles.segment} ${p.className}`}
              style={{ flexGrow: p.share }}
              title={`${formatShare(p.share)} — ${p.label}`}
            />
          ))}
      </div>
      <figcaption>
        <ul className={styles.legend}>
          {parts.map((p) => (
            <li key={p.key}>
              <span className={`${styles.swatch} ${p.className}`} aria-hidden="true" />
              <span className={styles.legendValue}>{formatShare(p.share)}</span> {p.label}
            </li>
          ))}
        </ul>
      </figcaption>
    </figure>
  );
}

export interface ColumnPoint {
  key: string;
  label: string;
  value: number;
}

/** Столбцы по времени: одна серия, подсказка при наведении, таблица-двойник в <details>. */
export function ColumnChart({ points, valueLabel }: { points: ColumnPoint[]; valueLabel: string }) {
  const [hover, setHover] = useState<number | null>(null);
  const max = Math.max(...points.map((p) => p.value), 1);
  const ticks = niceTicks(max);
  const top = ticks[ticks.length - 1] ?? max;
  // Подписи оси X — не на каждом столбце: первый, середина, последний
  const labelled = new Set([0, Math.floor((points.length - 1) / 2), points.length - 1]);
  const hovered = hover != null ? points[hover] : undefined;

  return (
    <figure className={styles.columns}>
      <div className={styles.plot} aria-hidden="true" onPointerLeave={() => setHover(null)}>
        <div className={styles.yAxis}>
          {[...ticks].reverse().map((t) => (
            <span key={t} className="tabular">
              {formatInt(t)}
            </span>
          ))}
        </div>
        <div className={styles.area}>
          {ticks.map((t) => (
            <span key={t} className={styles.gridline} style={{ bottom: `${(t / top) * 100}%` }} />
          ))}
          <div className={styles.cols}>
            {points.map((p, i) => (
              <span key={p.key} className={styles.colSlot} onPointerEnter={() => setHover(i)}>
                <span
                  className={`${styles.col} ${hover === i ? styles.colActive : ""}`}
                  style={{ height: p.value > 0 ? `max(${(p.value / top) * 100}%, 2px)` : 0 }}
                />
              </span>
            ))}
          </div>
          {hovered && hover != null && (
            <div
              // Сбоку от столбца, а не над ним: так подсказка не закрывает вершину, о которой спрашивают
              className={`${styles.tooltip} ${hover > points.length * 0.7 ? styles.tooltipLeft : ""}`}
              style={{
                left: `${((hover > points.length * 0.7 ? hover : hover + 1) / points.length) * 100}%`,
              }}
            >
              <strong className="tabular">{formatInt(hovered.value)}</strong>
              <span>{hovered.label}</span>
            </div>
          )}
        </div>
        <div className={styles.xAxis}>
          {points.map((p, i) => (
            <span key={p.key}>{labelled.has(i) ? p.label : ""}</span>
          ))}
        </div>
      </div>
      <details className={styles.table}>
        <summary>Таблица значений</summary>
        <table>
          <thead>
            <tr>
              <th scope="col">Период</th>
              <th scope="col">{valueLabel}</th>
            </tr>
          </thead>
          <tbody>
            {points.map((p) => (
              <tr key={p.key}>
                <th scope="row">{p.label}</th>
                <td className="tabular">{formatInt(p.value)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </figure>
  );
}

/** 0 и «круглые» деления до максимума: 0 / 5 / 10, 0 / 20 / 40 … */
export function niceTicks(max: number): number[] {
  const raw = max / 2;
  const pow = 10 ** Math.floor(Math.log10(raw));
  // Значения — счётчики статей, поэтому шаг не меньше 1
  const step = Math.max(1, [1, 2, 2.5, 5, 10].map((m) => m * pow).find((s) => s >= raw) ?? raw);
  const ticks = [0];
  while ((ticks[ticks.length - 1] ?? 0) < max) ticks.push(ticks.length * step);
  return ticks;
}
