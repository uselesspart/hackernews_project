import re
from pathlib import Path
from typing import List, Iterator, Set

_en_nlp = None 

try:
    import spacy
    _en_nlp = spacy.load("en_core_web_sm", exclude=["parser", "ner"])
except Exception:
    _en_nlp = None

WORD_PATTERN = re.compile(r"[A-Za-zА-Яа-яЁё]+(?:['-][A-Za-zА-Яа-яЁё]+)*|\d+")
TOKEN_PATTERN = re.compile(r"[A-Za-zА-Яа-яЁё]+(?:['-][A-Za-zА-Яа-яЁё]+)*|\d+|[^\w\s]")
SPLIT_RE = re.compile(r"[-']")

# Default words to preserve (not lemmatize)
DEFAULT_PRESERVE_WORDS = {
    # Operating systems - plural forms are significant
    "windows",
    
    #languages
    "c++",

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
SPLIT_RE = re.compile(r"[-']")

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
    
    cache: dict[str, str] = {}
    uniq, seen = [], set()
    
    for t in tokens:
        if t not in seen:
            uniq.append(t)
            seen.add(t)
    
    if _en_nlp is not None:
        for doc, t in zip(_en_nlp.pipe(uniq, batch_size=1000), uniq):
            if t.lower() in preserve_words:
                cache[t] = t
            else:
                cache[t] = (doc[0].lemma_ if len(doc) else t)
    else:
        for t in uniq:
            cache[t] = t
    
    return [cache[t] for t in tokens]

def tokenize_and_lemmatize(
    text: str,
    *,
    keep_punct: bool = False,
    num_token: str | None = "<NUM>",
    lower: bool = True,
    lemmatize_en: bool = True,
    preserve_words: Set[str] | None = None,
) -> List[str]:
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