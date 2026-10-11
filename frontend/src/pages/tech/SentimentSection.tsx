import { useState } from "react";

import type { CommentExample, TechProfile } from "../../api/types";
import { SentimentBar } from "../../components/charts";
import { ExternalIcon } from "../../components/icons";
import { Note, Section } from "../../components/ui";
import { COMMENTS, countLabel, formatSigned } from "../../lib/format";
import styles from "./tech.module.css";

/**
 * Сигнатурный момент страницы: цифры тона превращаются в реальные голоса.
 * Индекс и доли показываются только при достаточном числе комментариев,
 * а сами примеры — всегда: это не оценка, а цитаты со ссылкой на источник.
 */
export function SentimentSection({ profile }: { profile: TechProfile }) {
  const { sentiment: s, name } = profile;
  const hasShares = s.reliable && s.pos_share != null && s.neu_share != null && s.neg_share != null;

  return (
    <Section
      id="sentiment"
      title="Тон комментариев"
      lead={
        s.n > 0 ? (
          <>
            Оценено {countLabel(s.n, COMMENTS)} в обсуждениях статей о {name}. Тон определяется по всему
            комментарию, а не только по словам о самой технологии.
          </>
        ) : undefined
      }
    >
      {s.n === 0 ? (
        <Note>К статьям о {name} в выборке нет комментариев, поэтому тон оценить нельзя.</Note>
      ) : hasShares ? (
        <div className={styles.sentimentSummary}>
          <SentimentBar pos={s.pos_share ?? 0} neu={s.neu_share ?? 0} neg={s.neg_share ?? 0} />
          {s.index != null && (
            <p className={styles.index}>
              Индекс тона <strong className={styles.indexValue}>{formatSigned(s.index)}</strong>
              <span className={styles.indexScale}> — среднее по комментариям, шкала от −1 (негативно) до +1 (позитивно)</span>
            </p>
          )}
        </div>
      ) : (
        <Note tone="lowdata">
          Мало данных для оценки тона: {countLabel(s.n, COMMENTS)}. Доли и индекс покажем, когда комментариев станет
          больше — на такой выборке они меняются от пары случайных реплик.
        </Note>
      )}

      {(s.positive.length > 0 || s.negative.length > 0) && (
        <div id="voices" className={styles.voices}>
          <Voices title="Самые позитивные" tone="pos" items={s.positive} />
          <Voices title="Самые негативные" tone="neg" items={s.negative} />
        </div>
      )}
    </Section>
  );
}

function Voices({ title, tone, items }: { title: string; tone: "pos" | "neg"; items: CommentExample[] }) {
  if (items.length === 0) return null;
  return (
    <div className={styles.voiceCol}>
      <h3 className={styles.voiceTitle}>
        <span className={`${styles.voiceKey} ${tone === "pos" ? styles.keyPos : styles.keyNeg}`} aria-hidden="true" />
        {title}
      </h3>
      <ul className={styles.quotes}>
        {items.map((c) => (
          <li key={c.comment_id}>
            <Quote comment={c} />
          </li>
        ))}
      </ul>
    </div>
  );
}

// Бэкенд обрезает примеры до 600 знаков без многоточия
const BACKEND_CUT = 600;
const COLLAPSED_CHARS = 320;

function Quote({ comment }: { comment: CommentExample }) {
  const [open, setOpen] = useState(false);
  const long = comment.text.length > COLLAPSED_CHARS;
  const cut = comment.text.length >= BACKEND_CUT;
  const text = !long || open ? comment.text : `${comment.text.slice(0, COLLAPSED_CHARS).trimEnd()}`;
  return (
    <figure className={styles.quote}>
      <blockquote cite={comment.hn_url}>
        <p>
          {text}
          {(!open && long) || cut ? "…" : ""}
        </p>
      </blockquote>
      <figcaption className={styles.quoteFoot}>
        {long && (
          <button type="button" className={styles.linkButton} onClick={() => setOpen((v) => !v)} aria-expanded={open}>
            {open ? "Свернуть" : "Развернуть"}
          </button>
        )}
        <a href={comment.hn_url} rel="noopener noreferrer" className={styles.external}>
          Весь комментарий на HN
          <ExternalIcon className={styles.externalIcon} />
        </a>
      </figcaption>
    </figure>
  );
}
