import { useState } from "react";

import type { CommentExample, SentimentShares, TechProfile } from "../../api/types";
import { SentimentBar } from "../../components/charts";
import { ExternalIcon } from "../../components/icons";
import { Note, Section } from "../../components/ui";
import { COMMENTS, COMMENTS_IN, countLabel, formatSigned, REMARKS } from "../../lib/format";
import styles from "./tech.module.css";

/**
 * Сигнатурный момент страницы: цифры тона превращаются в реальные голоса.
 * Сначала тон реплик о самой технологии (ответ на вопрос «как говорят о Rust»),
 * под ним — тон всего обсуждения как фон. Доли — только при достаточной выборке,
 * цитаты — всегда: это не оценка, а первоисточник со ссылкой.
 */
export function SentimentSection({ profile }: { profile: TechProfile }) {
  const { sentiment: s, name } = profile;
  const withIndex = [s.aspect, s].some((t) => isShown(t) && t.index != null);

  return (
    <Section
      id="sentiment"
      title="Тон комментариев"
      lead={
        s.n > 0 ? (
          <>
            Оценено {countLabel(s.n, COMMENTS)} в обсуждениях статей о {name}
            {s.aspect.n > 0 ? `, из них ${name} прямо называют в ${countLabel(s.aspect.n, COMMENTS_IN)}` : ""}. Цитаты
            чужих реплик и код в оценку не входят.
          </>
        ) : undefined
      }
    >
      {s.n === 0 ? (
        <Note>К статьям о {name} в выборке нет комментариев, поэтому тон оценить нельзя.</Note>
      ) : (
        <div className={styles.toneRows}>
          <ToneRow
            title={`Когда говорят о ${name}`}
            caption="только предложения, где технология названа"
            tone={s.aspect}
            lowData={
              s.aspect.n === 0
                ? `${name} в этих комментариях прямо не называют — тон по отношению к технологии оценить не по чему.`
                : `Мало данных: ${countLabel(s.aspect.n, REMARKS)} о ${name}. Доли покажем, когда таких реплик станет больше.`
            }
          />
          <ToneRow
            title="Всё обсуждение"
            caption="комментарии целиком, о чём бы они ни были"
            tone={s}
            lowData={`Мало данных для оценки тона: ${countLabel(s.n, COMMENTS)}. Доли покажем, когда комментариев станет больше — на такой выборке они меняются от пары случайных реплик.`}
          />
          {withIndex && (
            <p className={styles.indexScale}>
              Индекс тона — среднее по репликам, шкала от −1 (негативно) до +1 (позитивно).
            </p>
          )}
        </div>
      )}

      {(s.positive.length > 0 || s.negative.length > 0) && (
        <div id="voices" className={styles.voices}>
          <Voices tone="pos" items={s.positive} name={name} />
          <Voices tone="neg" items={s.negative} name={name} />
        </div>
      )}
    </Section>
  );
}

function isShown(tone: SentimentShares): boolean {
  return tone.reliable && tone.pos_share != null && tone.neu_share != null && tone.neg_share != null;
}

function ToneRow({
  title,
  caption,
  tone,
  lowData,
}: {
  title: string;
  caption: string;
  tone: SentimentShares;
  lowData: string;
}) {
  return (
    <div className={styles.toneRow}>
      <h3 className={styles.toneTitle}>
        {title}
        <span className={styles.toneCaption}> — {caption}</span>
      </h3>
      {isShown(tone) ? (
        <>
          <SentimentBar pos={tone.pos_share ?? 0} neu={tone.neu_share ?? 0} neg={tone.neg_share ?? 0} />
          {tone.index != null && (
            <p className={styles.index}>
              Индекс тона <strong className={styles.indexValue}>{formatSigned(tone.index)}</strong>
            </p>
          )}
        </>
      ) : (
        <Note tone="lowdata">{lowData}</Note>
      )}
    </div>
  );
}

function Voices({ tone, items, name }: { tone: "pos" | "neg"; items: CommentExample[]; name: string }) {
  if (items.length === 0) return null;
  // Бэкенд берёт примеры из реплик о технологии, а если таких нет — из комментариев целиком;
  // подпись говорит, какой из двух случаев перед читателем
  const about = items.every((c) => c.mentions) ? `о ${name}` : "в обсуждениях";
  return (
    <div className={styles.voiceCol}>
      <h3 className={styles.voiceTitle}>
        <span className={`${styles.voiceKey} ${tone === "pos" ? styles.keyPos : styles.keyNeg}`} aria-hidden="true" />
        {tone === "pos" ? "Самые позитивные" : "Самые негативные"} {about}
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
