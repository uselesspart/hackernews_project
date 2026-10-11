import { useEffect, useState } from "react";

export function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = window.setTimeout(() => setDebounced(value), delayMs);
    return () => window.clearTimeout(id);
  }, [value, delayMs]);
  return debounced;
}

/**
 * true, только если active держится дольше delayMs.
 * Индикатор, мелькнувший на долю секунды, раздражает (NN/g: до ~1 с — ничего не показывать).
 */
export function useDelayedFlag(active: boolean, delayMs = 400): boolean {
  const [shown, setShown] = useState(false);
  useEffect(() => {
    if (!active) {
      setShown(false);
      return;
    }
    const id = window.setTimeout(() => setShown(true), delayMs);
    return () => window.clearTimeout(id);
  }, [active, delayMs]);
  return shown;
}

export function useDocumentTitle(title: string | null) {
  useEffect(() => {
    if (title) document.title = `${title} — технологии на Hacker News`;
    else document.title = "Технологии на Hacker News";
  }, [title]);
}
