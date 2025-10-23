import re
import argparse
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from utils.clean_text import clean_text
from collections import Counter

EN_STOP = {
    #html
    "href","rel","nofollow","https",

    # местоимения и указатели
    "i","me","my","mine","myself","we","us","our","ours","ourselves",
    "you","your","yours","yourself","yourselves",
    "he","him","his","himself","she","her","hers","herself",
    "it","its","itself","they","them","their","theirs","themselves","the",
    "one","ones","someone","somebody","something",
    "anyone","anybody","anything","everyone","everybody","everything",
    "noone","nobody","nothing","who","whom","whose","which","what",
    "where","when","why","how","this","that","these","those",
    "some","any","each","either","neither","both","few","many","much",
    "more","most","less","least","several","other","another","same","such","own", "use",

    # формы глаголов be/do/have и модальные
    "be","am","is","are","was","were","being","been",
    "do","does","did","doing",
    "have","has","had","having",
    "will","would","shall","should","can","could","may","might","must","ought",

    # отрицания и сокращения (в т.ч. без апострофа после очистки)
    "no","nor","not","cannot","ain",
    "don't","doesn't","isn't","aren't","wasn't","weren't","haven't","hasn't","hadn't",
    "didn't","won't","wouldn't","shan't","shouldn't","couldn't","mustn't","mightn't",
    "don","doesn","isn","aren","wasn","weren","haven","hasn","hadn","didn",
    "won","wouldn","shan","shouldn","couldn","mustn","mightn",
    "n't","ll","re","ve","d","s","y","t",

    # союзы, связки
    "and","or","if","then","else","than","because","so","though","although","while",
    "whereas","as","since","until","unless","yet","however","therefore","thus",

    # предлоги
    "about","above","below","under","over","into","onto","out","off","in","on","at","by",
    "from","to","of","for","with","without","within","through","across","against",
    "around","along","between","among","behind","beyond","during","before","after",
    "toward","towards","upon","via","per","but","also","need","take","see","say","all",
    "get","well","think","look","like","com","give","www","try","seem",

    # частые наречия/филлеры
    "very","too","just","quite","rather","really","almost","already","still",
    "ever","never","always","often","usually","sometimes",
    "maybe","perhaps","probably","anyway","anyhow","again","even",

    # указатели времени/места (часто малоинформативны)
    "here","there","elsewhere","anywhere","everywhere","now","soon","later",
    "today","yesterday","tomorrow",

    # и пр. служебные
    "etc","etc.","eg","e.g.","ie","i.e.",
    "please","thanks","thank","hi","hey","ok","okay","yes","yeah","yep","nope",

    # разговорные абстракции
    "thing","things","stuff","lot","lots","kind","kinda","sort","sorta",
    "part","bit","way","ways","point","points"
}

URL_RE = re.compile(r"https?://\S+|www\.\S+")
CODE_RE = re.compile(r"`[^`]+`|```.*?```", re.S)
HTML_RE = re.compile(r"<[^>]+>")
NON_ALPHA_RE = re.compile(r"[^a-zA-Zа-яА-Я0-9\- ]+")


def parse_args():
    p = argparse.ArgumentParser(
        prog="export_titles",
        description="Отрисовка облака слов для технологии"
    )
    p.add_argument("-i", "--input", required=True, help="Путь к входному файлу")
    p.add_argument("-o", "--output", required=True, help="Путь к выходному файлу")
    p.add_argument("--extra", help="Дополнительные слова, которые не нужно учитывать")
    return p.parse_args()

def tokenize(text: str):
    return [w for w in text.split() if len(w) > 2]

def build_frequencies(comments: list[str], extra_stop: set[str] = None):
    stop = EN_STOP
    if extra_stop:
        stop |= extra_stop
    counter = Counter()
    for c in comments:
        tokens = [w for w in tokenize(clean_text(c)) if w not in stop]
        counter.update(tokens)
    return dict(counter)

def main() -> int:
    args = parse_args()
    try:
        words = []
        with open(args.input, 'r') as f:
            for line in f:
                words.append(line.strip())
        extra_stop = {args.extra}
        freqs = build_frequencies(words, extra_stop=extra_stop)
        wordcloud = WordCloud(
            width=800,
            height=400,
            background_color='white',
            colormap='viridis'
            ).generate_from_frequencies(freqs)
        plt.figure(figsize=(10, 5))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off')
        plt.title("Example Word Cloud")
        plt.tight_layout()
        plt.savefig(args.output, dpi=300, bbox_inches='tight')
        print(f"Plot saved to {args.output}")
        return 0
    except Exception as e:
        print(f"Ошибка: {e}")
        return 1

if __name__ == "__main__":
    main()
