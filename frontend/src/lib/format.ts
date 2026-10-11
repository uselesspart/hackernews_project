const LOCALE = "ru-RU";

const intFmt = new Intl.NumberFormat(LOCALE);
const decFmt = new Intl.NumberFormat(LOCALE, { maximumFractionDigits: 1 });
const pctFmt = new Intl.NumberFormat(LOCALE, { style: "percent", maximumFractionDigits: 0 });
const pctFineFmt = new Intl.NumberFormat(LOCALE, { style: "percent", maximumFractionDigits: 1 });
const signedFmt = new Intl.NumberFormat(LOCALE, {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
  signDisplay: "exceptZero",
});
const pluralRules = new Intl.PluralRules(LOCALE);

// Даты в API без часового пояса и хранятся в UTC: показываем их в UTC, чтобы день не «съезжал»
const dateFmt = new Intl.DateTimeFormat(LOCALE, { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" });
const shortDateFmt = new Intl.DateTimeFormat(LOCALE, { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
const monthFmt = new Intl.DateTimeFormat(LOCALE, { month: "short", year: "numeric", timeZone: "UTC" });
const dayMonthFmt = new Intl.DateTimeFormat(LOCALE, { day: "numeric", month: "short", timeZone: "UTC" });

export const formatInt = (n: number) => intFmt.format(n);
export const formatDecimal = (n: number) => decFmt.format(n);
export const formatSigned = (n: number) => signedFmt.format(n);

/** Доля 0..1 → «9 %»; мелкие доли — с десятыми, чтобы не превращаться в «0 %». */
export function formatShare(share: number): string {
  return share > 0 && share < 0.095 ? pctFineFmt.format(share) : pctFmt.format(share);
}

/** Склонение: plural(5, ["статья", "статьи", "статей"]) → «статей». */
export function plural(n: number, forms: readonly [one: string, few: string, many: string]): string {
  if (!Number.isInteger(n)) return forms[1];
  const rule = pluralRules.select(n);
  return rule === "one" ? forms[0] : rule === "few" ? forms[1] : forms[2];
}

export const countLabel = (n: number, forms: readonly [string, string, string]) => `${formatInt(n)} ${plural(n, forms)}`;

export const STORIES = ["статья", "статьи", "статей"] as const;
export const COMMENTS = ["комментарий", "комментария", "комментариев"] as const;
export const DAYS = ["день", "дня", "дней"] as const;

export function parseApiDate(value: string): Date {
  return new Date(/[zZ]|[+-]\d\d:\d\d$/.test(value) ? value : `${value}Z`);
}

export const formatDate = (value: string) => dateFmt.format(parseApiDate(value));
export const formatShortDate = (value: string) => shortDateFmt.format(parseApiDate(value));
export const formatMonth = (value: string) => monthFmt.format(parseApiDate(value));
export const formatDayMonth = (value: string) => dayMonthFmt.format(parseApiDate(value));

/** Точка в конце предложения, если строка уже не кончается на «г.» и т. п. */
export const endSentence = (s: string) => (s.endsWith(".") ? s : `${s}.`);

/** «11–13 апреля 2024 г.» */
export function formatPeriod(start: string, end: string): string {
  return dateFmt.formatRange(parseApiDate(start), parseApiDate(end));
}

export function spanDays(start: string, end: string): number {
  return (parseApiDate(end).getTime() - parseApiDate(start).getTime()) / 86_400_000;
}

/** IRR → «в 1,8 раза» / «в 3 раза» / «в 5 раз». */
export function timesLabel(ratio: number): string {
  const rounded = Math.round(ratio * 10) / 10;
  const word = Number.isInteger(rounded) ? plural(rounded, ["раз", "раза", "раз"]) : "раза";
  return `в ${decFmt.format(rounded)} ${word}`;
}

export function hostOf(url: string | null | undefined): string | null {
  if (!url) return null;
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return null;
  }
}
