import type { ReactNode } from "react";

import { InfoIcon } from "./icons";
import styles from "./ui.module.css";

export function Section({
  id,
  title,
  lead,
  children,
  aside,
}: {
  id: string;
  title: string;
  lead?: ReactNode;
  children: ReactNode;
  aside?: ReactNode;
}) {
  return (
    <section id={id} aria-labelledby={`${id}-title`} className={styles.section}>
      <div className={styles.sectionHead}>
        <div>
          <h2 id={`${id}-title`}>{title}</h2>
          {lead && <p className={styles.sectionLead}>{lead}</p>}
        </div>
        {aside}
      </div>
      {children}
    </section>
  );
}

/** Служебное пояснение: «мало данных», ограничения метода. Не результат, а статус. */
export function Note({ children, tone = "info" }: { children: ReactNode; tone?: "info" | "lowdata" }) {
  return (
    <div className={`${styles.note} ${tone === "lowdata" ? styles.lowdata : ""}`}>
      <InfoIcon className={styles.noteIcon} />
      <div>{children}</div>
    </div>
  );
}

export function StatRow({ children }: { children: ReactNode }) {
  return <dl className={styles.statRow}>{children}</dl>;
}

export function StatTile({ label, value, hint }: { label: string; value: ReactNode; hint?: ReactNode }) {
  return (
    <div className={styles.stat}>
      <dt className={styles.statLabel}>{label}</dt>
      <dd className={styles.statValue}>{value}</dd>
      {hint && <dd className={styles.statHint}>{hint}</dd>}
    </div>
  );
}

export function Skeleton({ height = 16, width = "100%" }: { height?: number | string; width?: number | string }) {
  return <span className={styles.skeleton} style={{ height, width }} aria-hidden="true" />;
}

export function ErrorState({
  title,
  children,
  onRetry,
  alert = true,
  level = 2,
}: {
  title: string;
  children?: ReactNode;
  onRetry?: () => void;
  /** Сбой объявляется экранным диктором сразу; обычная страница «не найдено» — нет */
  alert?: boolean;
  /** 1 — страница целиком, 3 — блок внутри раздела */
  level?: 1 | 2 | 3;
}) {
  const Heading = `h${level}` as const;
  return (
    <div className={styles.state} role={alert ? "alert" : undefined}>
      <Heading className={styles.stateTitle}>{title}</Heading>
      {children && <div className={styles.stateText}>{children}</div>}
      {onRetry && (
        <button type="button" className={styles.button} onClick={onRetry}>
          Повторить
        </button>
      )}
    </div>
  );
}

export function Button({
  children,
  onClick,
  disabled,
  busy,
}: {
  children: ReactNode;
  onClick: () => void;
  disabled?: boolean;
  busy?: boolean;
}) {
  return (
    <button type="button" className={styles.button} onClick={onClick} disabled={disabled} aria-busy={busy}>
      {children}
    </button>
  );
}

export function Chip({ children }: { children: ReactNode }) {
  return <span className={styles.chip}>{children}</span>;
}
