import { useEffect, useRef } from "react";
import { Link, Outlet, ScrollRestoration, useLocation } from "react-router-dom";

import { useMeta } from "../api/queries";
import { endSentence, formatDate, formatPeriod } from "../lib/format";
import { useTheme } from "../lib/theme";
import { MonitorIcon, MoonIcon, SunIcon } from "./icons";
import styles from "./Layout.module.css";
import { SearchBox } from "./SearchBox";

const THEME_LABEL = { system: "как в системе", light: "светлая", dark: "тёмная" } as const;

export function Layout() {
  const location = useLocation();
  const isHome = location.pathname === "/";
  const mainRef = useRef<HTMLElement>(null);
  const prevPath = useRef(location.pathname);

  // После перехода по ссылке фокус и экранный диктор начинают с нового содержимого, а не со ссылки старой страницы.
  // Сравнение с прошлым путём, а не флаг «первый рендер»: StrictMode повторно запускает эффекты при монтировании
  useEffect(() => {
    if (prevPath.current === location.pathname) return;
    prevPath.current = location.pathname;
    mainRef.current?.focus({ preventScroll: true });
  }, [location.pathname]);

  return (
    <div className={styles.shell}>
      <a className={styles.skip} href="#main">
        К содержимому
      </a>
      <header className={styles.header}>
        <div className={styles.headerInner}>
          <Link to="/" className={styles.brand} aria-label="Технологии на Hacker News — на главную">
            <span className={styles.mark} aria-hidden="true">
              HN
            </span>
            <span className={styles.brandText}>технологии</span>
          </Link>
          <div className={styles.headerSearch}>{!isHome && <SearchBox variant="compact" hotkey />}</div>
          <ThemeToggle />
        </div>
      </header>
      <main id="main" ref={mainRef} tabIndex={-1} className={styles.main}>
        <Outlet />
      </main>
      <Footer />
      <ScrollRestoration />
    </div>
  );
}

function ThemeToggle() {
  const { theme, cycle } = useTheme();
  const Icon = theme === "light" ? SunIcon : theme === "dark" ? MoonIcon : MonitorIcon;
  return (
    <button
      type="button"
      className={styles.iconButton}
      onClick={cycle}
      aria-label={`Тема: ${THEME_LABEL[theme]}. Переключить`}
      title={`Тема: ${THEME_LABEL[theme]}`}
    >
      <Icon className={styles.icon} />
    </button>
  );
}

function Footer() {
  const meta = useMeta().data;
  return (
    <footer className={styles.footer}>
      <div className={styles.footerInner}>
        {meta?.period_start && meta.period_end && (
          <p>
            {endSentence(
              `Данные: статьи и комментарии Hacker News за ${formatPeriod(meta.period_start, meta.period_end)}` +
                (meta.computed_at ? `, пересчитаны ${formatDate(meta.computed_at)}` : ""),
            )}
          </p>
        )}
        <p>
          Независимый проект, не связан с Hacker News и Y Combinator. Данные получены через{" "}
          <a href="https://github.com/HackerNews/API" rel="noopener noreferrer">
            открытый API Hacker News
          </a>
          .
        </p>
      </div>
    </footer>
  );
}
