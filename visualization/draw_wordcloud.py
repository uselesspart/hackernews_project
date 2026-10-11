import argparse
from pathlib import Path

from wordcloud import WordCloud

from utils.cli import cli_main
from utils.io import read_nonempty_lines
from utils.words import build_frequencies
from visualization._common import plt, save_figure


def parse_args():
    p = argparse.ArgumentParser(
        prog="draw_wordcloud",
        description="Отрисовка облака слов для технологии"
    )
    p.add_argument("-i", "--input", required=True, help="Файл комментариев технологии (например, rust_5_lem.txt)")
    p.add_argument("-o", "--output", required=True, help="Путь к выходному изображению")
    p.add_argument("--extra", help="Дополнительное слово, которое не нужно учитывать (обычно сама технология)")
    return p.parse_args()


@cli_main
def main() -> int:
    args = parse_args()
    extra_stop = {args.extra.lower()} if args.extra else set()
    freqs = build_frequencies(read_nonempty_lines(args.input), extra_stop=extra_stop)
    wordcloud = WordCloud(width=800, height=400, background_color='white',
                          colormap='viridis').generate_from_frequencies(freqs)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(wordcloud, interpolation='bilinear')
    ax.axis('off')
    # "rust_5_lem.txt" -> "rust"
    ax.set_title(Path(args.input).stem.split("_")[0])
    fig.tight_layout()
    save_figure(fig, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
