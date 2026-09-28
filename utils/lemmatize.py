import re
from pathlib import Path
from typing import List, Iterator, Set

_en_nlp = None 

try:
    import spacy
    _en_nlp = spacy.load("en_core_web_sm", exclude=["parser", "ner"])
except Exception:
    _en_nlp = None

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

def load_preserve_words(path: Path | None) -> Set[str]:
    words = DEFAULT_PRESERVE_WORDS.copy()
    
    if path and path.exists():
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                word = line.strip().lower()
                if word and not word.startswith("#"):
                    words.add(word)
        print(f"Loaded {len(words)} preserve words from {path}")
    
    return words

def _lemmatize_en_batch(tokens: List[str], preserve_words: Set[str] | None = None) -> List[str]:
    if _en_nlp is None:
        return tokens
    
    if preserve_words is None:
        preserve_words = set()
    
    cache: dict[str, List[str]] = {}
    uniq, seen = [], set()

    for t in tokens:
        if t not in seen:
            uniq.append(t)
            seen.add(t)

    for doc, t in zip(_en_nlp.pipe(uniq, batch_size=1000), uniq):
        if t.lower() in preserve_words or len(doc) == 0:
            cache[t] = [t]
        elif len(doc) == 1:
            cache[t] = [doc[0].lemma_]
        elif "'" in t:
            # Сокращения: "don't" -> ["do", "not"]; раньше оставалось только "do",
            # и отрицание терялось. Притяжательное "'s" отбрасываем.
            cache[t] = [tok.lemma_ for tok in doc if tok.lemma_ not in ("'s", "'")]
        else:
            # Составные слова через дефис/подчёркивание оставляем одним токеном
            cache[t] = [t]

    return [lemma for t in tokens for lemma in cache[t]]

def tokenize_and_lemmatize(
    text: str,
    *,
    keep_punct: bool = False,
    num_token: str | None = "<NUM>",
    lower: bool = True,
    lemmatize_en: bool = True,
    preserve_words: Set[str] | None = None,
) -> List[str]:
    text = canonicalize_tech_mentions(text)
    if lower:
        text = text.lower()

    pattern = TOKEN_PATTERN if keep_punct else WORD_PATTERN
    tokens = pattern.findall(text)
    
    if not tokens:
        return []
    
    tokens = [(num_token if num_token is not None and t.isdigit() else t) for t in tokens]
    
    if lemmatize_en:
        tokens = _lemmatize_en_batch(tokens, preserve_words)
    
    return tokens

def iter_tokenized_lines(
    path: str | Path,
    *,
    keep_punct: bool = False,
    num_token: str | None = "<NUM>",
    lower: bool = True,
    lemmatize_en: bool = True,
    preserve_empty: bool = False,
    preserve_words: Set[str] | None = None,
) -> Iterator[List[str]]:
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
                preserve_words=preserve_words,
            )