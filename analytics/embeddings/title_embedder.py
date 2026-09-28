import gzip
import json
from pathlib import Path

from utils.lemmatize import iter_tokenized_lines


def save_token_matrix_jsonl_gz(
    src_path: str | Path,
    out_path: str | Path,
    *,
    keep_punct: bool = False,
    num_token: str | None = "<NUM>",
    lower: bool = True,
    lemmatize_en: bool = True,
) -> None:
    """TXT (строка = предложение) -> JSONL.GZ (строка = JSON-список токенов) для обучения Word2Vec."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with gzip.open(out, "wt", encoding="utf-8") as gzf:
        for tokens in iter_tokenized_lines(
            src_path,
            keep_punct=keep_punct,
            num_token=num_token,
            lower=lower,
            lemmatize_en=lemmatize_en,
        ):
            gzf.write(json.dumps(tokens, ensure_ascii=False) + "\n")
            count += 1
    print(f"Сохранено {count} строк в {out}")
