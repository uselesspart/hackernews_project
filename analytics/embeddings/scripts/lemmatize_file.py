import argparse
from pathlib import Path
from utils.lemmatize import load_preserve_words, iter_tokenized_lines

def parse_args():
    p = argparse.ArgumentParser(description="Лемматизация заголовков из TXT → TXT (по строкам).")
    p.add_argument("--input", "-i", type=Path, required=True,
                    help="Входной TXT (по одному заголовку на строку)")
    p.add_argument("--output", "-o", type=Path, required=True,
                    help="Выходной TXT (леммы по строкам)")
    p.add_argument("--keep-punct", action="store_true", default=False,
                    help="Оставлять знаки препинания как отдельные токены")
    p.add_argument("--no-lemmatize", action="store_true",
                    help="Только токенизация, без лемматизации")
    p.add_argument("--num-token", type=str, default="<NUM>",
                    help="Маркер для чисел (None, чтобы оставить как есть)")
    p.add_argument("--no-lower", action="store_true",
                    help="Не приводить к нижнему регистру перед лемматизацией")
    p.add_argument("--preserve-words", type=Path, default=None,
                    help="Файл со словами, которые не нужно лемматизировать (по одному на строку)")
    p.add_argument("--add-preserve", nargs="+", default=[],
                    help="Дополнительные слова для сохранения (не лемматизировать)")
    return p.parse_args()

def main():
    args = parse_args()

    num_token = None if args.num_token.lower() == "none" else args.num_token
    
    preserve_words = load_preserve_words(args.preserve_words)
    
    for word in args.add_preserve:
        preserve_words.add(word.lower())
    
    print(f"Preserving {len(preserve_words)} words from lemmatization")
    if args.preserve_words or args.add_preserve:
        print(f"Examples: {sorted(list(preserve_words))[:10]}")

    with args.output.open("w", encoding="utf-8") as out:
        for tokens in iter_tokenized_lines(
            path=args.input,
            keep_punct=args.keep_punct,
            num_token=num_token,
            lower=(not args.no_lower),
            lemmatize_en=(not args.no_lemmatize),
            preserve_words=preserve_words,
        ):
            out.write((" ".join(tokens) if tokens else "") + "\n")

    print(f"Processed {args.input} -> {args.output}")


if __name__ == "__main__":
    raise SystemExit(main())
