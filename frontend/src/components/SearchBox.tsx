import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useId, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";

import { getJson } from "../api/client";
import { useSuggest } from "../api/queries";
import type { Suggestion } from "../api/types";
import { countLabel, plural, STORIES } from "../lib/format";
import { useDebouncedValue } from "../lib/hooks";
import { SearchIcon } from "./icons";
import styles from "./SearchBox.module.css";

const LIMIT = 8;
// Около 150 мс: короче — запрос на каждую букву, длиннее — подсказки заметно отстают от ввода
const DEBOUNCE_MS = 150;

interface Props {
  variant?: "hero" | "compact";
  /** Фокус по клавише «/» — только у одного поля на странице */
  hotkey?: boolean;
}

export function SearchBox({ variant = "compact", hotkey = false }: Props) {
  const id = useId();
  const inputId = `${id}-input`;
  const listId = `${id}-list`;
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [value, setValue] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);

  const q = value.trim();
  const debounced = useDebouncedValue(q, DEBOUNCE_MS);
  const query = useSuggest(debounced, open, LIMIT);
  const items = query.data ?? [];
  const fresh = !query.isPlaceholderData && debounced === q;
  const notFound = fresh && query.isSuccess && q !== "" && items.length === 0;
  const expanded = open && (items.length > 0 || notFound || query.isError);

  useEffect(() => setActive(-1), [debounced]);

  useEffect(() => {
    if (!hotkey) return;
    const onKey = (e: globalThis.KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      const typing = target?.closest("input, textarea, select, [contenteditable='true']");
      if (e.key === "/" && !typing && !e.ctrlKey && !e.metaKey && !e.altKey) {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [hotkey]);

  function choose(item: Suggestion) {
    setValue("");
    setOpen(false);
    inputRef.current?.blur();
    navigate(`/tech/${item.key}`);
  }

  async function chooseFirst() {
    if (fresh) {
      if (items[0]) choose(items[0]);
      return;
    }
    // Enter нажали раньше, чем отработал debounce: спрашиваем API сразу по текущему тексту
    const result = await queryClient.fetchQuery({
      queryKey: ["suggest", q, LIMIT],
      queryFn: ({ signal }) => getJson<Suggestion[]>("/techs/suggest", { q, limit: LIMIT }, signal),
    });
    if (result[0]) choose(result[0]);
  }

  function onKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        if (!open) setOpen(true);
        else if (items.length) setActive((i) => (i + 1) % items.length);
        break;
      case "ArrowUp":
        e.preventDefault();
        if (items.length) setActive((i) => (i <= 0 ? items.length - 1 : i - 1));
        break;
      case "Enter": {
        e.preventDefault();
        const picked = active >= 0 ? items[active] : undefined;
        if (picked) choose(picked);
        else if (q) void chooseFirst();
        break;
      }
      case "Escape":
        if (expanded) setOpen(false);
        else setValue("");
        break;
      case "Tab":
        setOpen(false);
        break;
    }
  }

  const activeId = active >= 0 ? `${id}-opt-${active}` : undefined;
  const status = !expanded
    ? ""
    : query.isError
      ? "Поиск временно недоступен"
      : notFound
        ? "Ничего не найдено"
        : `${items.length} ${plural(items.length, ["подсказка", "подсказки", "подсказок"])}`;

  return (
    <form role="search" className={`${styles.root} ${styles[variant]}`} onSubmit={(e) => e.preventDefault()}>
      <label htmlFor={inputId} className={variant === "hero" ? styles.label : "visually-hidden"}>
        Найти технологию
      </label>
      <div className={styles.field}>
        <SearchIcon className={styles.icon} />
        <input
          ref={inputRef}
          id={inputId}
          className={styles.input}
          type="text"
          role="combobox"
          aria-expanded={expanded}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={activeId}
          autoComplete="off"
          autoCapitalize="off"
          spellCheck={false}
          enterKeyHint="search"
          placeholder={variant === "hero" ? "Rust, PostgreSQL, golang, Claude…" : "Найти технологию"}
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onClick={() => setOpen(true)}
          onBlur={() => setOpen(false)}
          onKeyDown={onKeyDown}
        />
        {hotkey && (
          <kbd className={styles.kbd} aria-hidden="true">
            /
          </kbd>
        )}
      </div>

      <div className={styles.popover} hidden={!expanded}>
        {expanded && q === "" && items.length > 0 && <p className={styles.heading}>Чаще всего в заголовках</p>}
        <ul id={listId} role="listbox" aria-label="Подсказки" className={styles.list}>
          {items.map((item, i) => (
            <li
              key={item.key}
              id={`${id}-opt-${i}`}
              role="option"
              aria-selected={i === active}
              className={styles.option}
              // mousedown, а не click: иначе blur инпута закроет список раньше выбора
              onMouseDown={(e) => {
                e.preventDefault();
                choose(item);
              }}
              onMouseMove={() => setActive(i)}
            >
              <span className={styles.name}>
                <Highlight text={item.name} query={item.matched ? "" : q} />
              </span>
              <span className={styles.meta}>
                {item.matched && (
                  <>
                    по запросу «<Highlight text={item.matched} query={q} />»{" · "}
                  </>
                )}
                {item.category ? `${item.category} · ` : ""}
                {item.stories > 0 ? countLabel(item.stories, STORIES) : "нет статей в выборке"}
              </span>
            </li>
          ))}
        </ul>
        {notFound && (
          <p className={styles.empty}>
            «{q}» мы не отслеживаем. Попробуйте другое написание или синоним: «golang», «postgres», «anthropic».
          </p>
        )}
        {open && query.isError && <p className={styles.empty}>Поиск временно недоступен. Попробуйте через минуту.</p>}
      </div>
      <p role="status" className="visually-hidden">
        {status}
      </p>
    </form>
  );
}

function Highlight({ text, query }: { text: string; query: string }): ReactNode {
  const i = query ? text.toLowerCase().indexOf(query.toLowerCase()) : -1;
  if (i < 0) return text;
  return (
    <>
      {text.slice(0, i)}
      <mark>{text.slice(i, i + query.length)}</mark>
      {text.slice(i + query.length)}
    </>
  );
}
