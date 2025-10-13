import re
import argparse
from pathlib import Path
from typing import List, Iterator

_en_nlp = None       # spaCy для английского

try:
    import spacy
    # Лёгкая загрузка без парсера/NER
    _en_nlp = spacy.load("en_core_web_sm", exclude=["parser", "ner"])
except Exception:
    _en_nlp = None

# Регэкспы для токенизации
WORD_PATTERN = re.compile(r"[A-Za-zА-Яа-яЁё]+(?:['-][A-Za-zА-Яа-яЁё]+)*|\d+")
TOKEN_PATTERN = re.compile(r"[A-Za-zА-Яа-яЁё]+(?:['-][A-Za-zА-Яа-яЁё]+)*|\d+|[^\w\s]")
SPLIT_RE = re.compile(r"[-']")  # для дефисных/апострофных слов в русском

def _lemmatize_en_batch(tokens: List[str]) -> List[str]:
    if _en_nlp is None and _en_stem is None:
        # Если ни spaCy, ни NLTK — возвращаем как есть
        return tokens
    # Кэш по уникальным токенам — ускоряет
    cache: dict[str, str] = {}
    uniq, seen = [], set()
    for t in tokens:
        if t not in seen:
            uniq.append(t); seen.add(t)
    if _en_nlp is not None:
        for doc, t in zip(_en_nlp.pipe(uniq, batch_size=1000), uniq):
            cache[t] = (doc[0].lemma_ if len(doc) else t)
    else:
        for t in uniq:
            cache[t] = _en_stem.stem(t) if _en_stem else t
    return [cache[t] for t in tokens]

def tokenize_and_lemmatize(
    text: str,
    *,
    keep_punct: bool = False,
    num_token: str | None = "<NUM>",
    lower: bool = True,
    lemmatize_en: bool = True,
) -> List[str]:
    """Токенизирует строку и опционально лемматизирует английские токены."""
    if lower:
        text = text.lower()
    pattern = TOKEN_PATTERN if keep_punct else WORD_PATTERN
    tokens = pattern.findall(text)
    if not tokens:
        return []
    tokens = [(num_token if num_token is not None and t.isdigit() else t) for t in tokens]
    if lemmatize_en:
        tokens = _lemmatize_en_batch(tokens)
    return tokens

def iter_tokenized_lines(
    path: str | Path,
    *,
    keep_punct: bool = False,
    num_token: str | None = "<NUM>",
    lower: bool = True,
    lemmatize_en: bool = True,
    preserve_empty: bool = False,
) -> Iterator[List[str]]:
    """Итерирует строки файла, отдаёт токены/леммы по строкам."""
    with Path(path).open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n")
            if not line.strip():
                if preserve_empty:
                    yield []
                continue
            yield tokenize_and_lemmatize(
                line,
                keep_punct=keep_punct,
                num_token=num_token,
                lower=lower,
                lemmatize_en=lemmatize_en,
            )


def main():
    ap = argparse.ArgumentParser(description="Лемматизация заголовков из TXT → TXT (по строкам).")
    ap.add_argument("--input", "-i", type=Path, required=True, help="Входной TXT (по одному заголовку на строку)")
    ap.add_argument("--output", "-o", type=Path, required=True, help="Выходной TXT (леммы по строкам)")
    ap.add_argument("--keep-punct", action="store_true", default=False,
                help="Оставлять знаки препинания как отдельные токены")
    ap.add_argument("--no-lemmatize", action="store_true", help="Только токенизация, без лемматизации")
    ap.add_argument("--num-token", type=str, default="<NUM>", help="Маркер для чисел (None, чтобы оставить как есть)")
    ap.add_argument("--no-lower", action="store_true", help="Не приводить к нижнему регистру перед лемматизацией")
    args = ap.parse_args()

    num_token = None if args.num_token.lower() == "none" else args.num_token

    with args.output.open("w", encoding="utf-8") as out:
        for tokens in iter_tokenized_lines(
            path=args.input,
            keep_punct=args.keep_punct,
            num_token=num_token,
            lower=(not args.no_lower),
        ):
            # Пишем леммы, разделённые пробелами. Пустые строки сохраняем.
            out.write((" ".join(tokens) if tokens else "") + "\n")


if __name__ == "__main__":
    main()