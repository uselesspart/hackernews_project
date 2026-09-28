import re
from collections.abc import Iterable, Iterator
from pathlib import Path

_en_nlp = None
_en_nlp_error: Exception | None = None

try:
    import spacy
    _en_nlp = spacy.load("en_core_web_sm", exclude=["parser", "ner"])
except Exception as e:  # импорт модуля не должен падать: лемматизация нужна не всем скриптам
    _en_nlp_error = e


def _require_nlp():
    """spaCy-пайплайн или понятная ошибка — вместо тихого отказа от лемматизации."""
    if _en_nlp is None:
        raise RuntimeError(
            f"Лемматизация недоступна: не удалось загрузить spaCy en_core_web_sm ({_en_nlp_error!r}). "
            "Установите зависимости из requirements.txt или отключите лемматизацию (--no-lemmatize)."
        )
    return _en_nlp

WORD_PATTERN = re.compile(r"[A-Za-zА-Яа-яЁё]+(?:['_-][A-Za-zА-Яа-яЁё]+)*|\d+")
TOKEN_PATTERN = re.compile(r"[A-Za-zА-Яа-яЁё]+(?:['_-][A-Za-zА-Яа-яЁё]+)*|\d+|[^\w\s]")

# Названия технологий, которые WORD_PATTERN иначе разрушает ("c++" -> "c",
# ".net" -> "net"), заменяются до токенизации на токены, совпадающие
# с каноническими именами из patterns.py / utils.groups.
TECH_SUBSTITUTIONS = [
    (re.compile(r"(?<!\w)c\+\+(?!\+)", re.IGNORECASE), " cpp "),
    (re.compile(r"(?<!\w)c#(?![\w#])", re.IGNORECASE), " csharp "),
    (re.compile(r"(?<!\w)f#(?![\w#])", re.IGNORECASE), " fsharp "),
    (re.compile(r"\b(?:asp|ado)\.net\b", re.IGNORECASE), " dotnet "),
    (re.compile(r"(?<![\w.])\.net\b", re.IGNORECASE), " dotnet "),
    (re.compile(r"\b(node|vue|next|react)\.js\b", re.IGNORECASE), lambda m: f" {m.group(1).lower()}js "),
    (re.compile(r"\bstable\s+diffusion\b", re.IGNORECASE), " stable_diffusion "),
    (re.compile(r"\bsql\s+server\b", re.IGNORECASE), " sqlserver "),
]
TECH_TOKENS = {"cpp", "csharp", "fsharp", "dotnet", "nodejs", "vuejs", "nextjs",
               "reactjs", "stable_diffusion", "sqlserver"}


def canonicalize_tech_mentions(text: str) -> str:
    for pattern, repl in TECH_SUBSTITUTIONS:
        text = pattern.sub(repl, text)
    return text


# Default words to preserve (not lemmatize)
DEFAULT_PRESERVE_WORDS = {
    # Operating systems - plural forms are significant
    "windows",

    # Canonical tech tokens (see TECH_SUBSTITUTIONS)
    *TECH_TOKENS,

    # Brand names / proper nouns
    "kubernetes",
    "jenkins",
    "postgres",
    "redis",

    # Acronyms that might get lemmatized incorrectly
    "aws",
    "gcp",
    "ios",
    "macos",
}

def load_preserve_words(path: Path | None) -> set[str]:
    words = DEFAULT_PRESERVE_WORDS.copy()

    if path and path.exists():
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                word = line.strip().lower()
                if word and not word.startswith("#"):
                    words.add(word)
        print(f"Загружено {len(words)} защищённых слов из {path}")

    return words

# Кэш "токен -> леммы" на весь процесс. Словарь корпуса быстро насыщается (закон Ципфа),
# поэтому spaCy вызывается почти только для новых слов. Слова из preserve_words
# проверяются до кэша, так что кэш от них не зависит.
_LEMMA_CACHE: dict[str, tuple[str, ...]] = {}
_LEMMA_CACHE_MAX = 2_000_000


def _lemmas_from_doc(token: str, doc) -> tuple[str, ...]:
    if len(doc) == 0:
        return (token,)
    if len(doc) == 1:
        return (doc[0].lemma_,)
    if "'" in token:
        # Сокращения: "don't" -> ("do", "not"); притяжательное "'s" отбрасываем
        return tuple(tok.lemma_ for tok in doc if tok.lemma_ not in ("'s", "'"))
    # Составные слова через дефис/подчёркивание оставляем одним токеном
    return (token,)


def _fill_lemma_cache(tokens: Iterable[str], preserve_words: set[str]) -> None:
    missing = list({t for t in tokens if t not in _LEMMA_CACHE and t.lower() not in preserve_words})
    if not missing:
        return
    nlp = _require_nlp()
    if len(_LEMMA_CACHE) + len(missing) > _LEMMA_CACHE_MAX:
        _LEMMA_CACHE.clear()
    for doc, t in zip(nlp.pipe(missing, batch_size=1000), missing):
        _LEMMA_CACHE[t] = _lemmas_from_doc(t, doc)


def _apply_lemmas(tokens: list[str], preserve_words: set[str]) -> list[str]:
    out: list[str] = []
    for t in tokens:
        if t.lower() in preserve_words:
            out.append(t)
        else:
            out.extend(_LEMMA_CACHE[t])
    return out


def _lemmatize_en_batch(tokens: list[str], preserve_words: set[str] | None = None) -> list[str]:
    preserve_words = preserve_words or set()
    _fill_lemma_cache(tokens, preserve_words)
    return _apply_lemmas(tokens, preserve_words)

def tokenize_and_lemmatize(
    text: str,
    *,
    keep_punct: bool = False,
    num_token: str | None = "<NUM>",
    lower: bool = True,
    lemmatize_en: bool = True,
    preserve_words: set[str] | None = None,
) -> list[str]:
    tokens = _tokenize(text, keep_punct=keep_punct, num_token=num_token, lower=lower)
    if tokens and lemmatize_en:
        tokens = _lemmatize_en_batch(tokens, preserve_words)
    return tokens


def _tokenize(text: str, *, keep_punct: bool, num_token: str | None, lower: bool) -> list[str]:
    text = canonicalize_tech_mentions(text)
    if lower:
        text = text.lower()
    pattern = TOKEN_PATTERN if keep_punct else WORD_PATTERN
    return [(num_token if num_token is not None and t.isdigit() else t) for t in pattern.findall(text)]

def iter_tokenized_lines(
    path: str | Path,
    *,
    keep_punct: bool = False,
    num_token: str | None = "<NUM>",
    lower: bool = True,
    lemmatize_en: bool = True,
    preserve_empty: bool = False,
    preserve_words: set[str] | None = None,
    chunk_size: int = 5000,
) -> Iterator[list[str]]:
    lemmatize = lemmatize_en
    if lemmatize:
        _require_nlp()  # падаем сразу, а не после чтения первого чанка
    preserve_words = preserve_words or set()

    def process(chunk: list[list[str] | None]) -> Iterator[list[str]]:
        # Все новые слова чанка лемматизируются одним вызовом spaCy
        if lemmatize:
            _fill_lemma_cache((t for tokens in chunk if tokens for t in tokens), preserve_words)
        for tokens in chunk:
            if tokens is None:
                yield []
            else:
                yield _apply_lemmas(tokens, preserve_words) if lemmatize else tokens

    chunk: list[list[str] | None] = []
    with Path(path).open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n")
            if not line.strip():
                if preserve_empty:
                    chunk.append(None)
            else:
                chunk.append(_tokenize(line, keep_punct=keep_punct, num_token=num_token, lower=lower))
            if len(chunk) >= chunk_size:
                yield from process(chunk)
                chunk = []
    yield from process(chunk)
