import argparse
import pandas as pd
from sklearn.manifold import TSNE
import matplotlib.pyplot as plt
import pandas as pd
from adjustText import adjust_text

def parse_args():
    p = argparse.ArgumentParser(
        prog="export_titles",
        description="Отрисовка карты отношений между словами"
    )
    p.add_argument("-m", "--matrix", required=True, help="Путь к файлу с матрицей схожести")
    p.add_argument("-t", "--tech", required=True, help="Путь к файлу со списком технологий")
    p.add_argument("-o", "--output", required=True, help="Путь к выходному файлу")
    return p.parse_args()

def main() -> int:
    args = parse_args()
    try:

        words_of_interest = []
        with open(args.tech, 'r') as f:
            for line in f:
                words_of_interest.append(line.strip())

        df = pd.read_csv(args.matrix, index_col=0)

        words_of_interest = [w for w in words_of_interest if w in df.index]
        
        word_vectors = df.loc[words_of_interest]

        tsne = TSNE(n_components=2, random_state=42, perplexity=min(30, len(words_of_interest)-1))
        embeddings_2d = tsne.fit_transform(word_vectors)

        plt.figure(figsize=(12, 8))
        plt.scatter(embeddings_2d[:, 0], embeddings_2d[:, 1], s=100, alpha=0.6)

        texts = []
        for i, word in enumerate(words_of_interest):
            txt = plt.text(embeddings_2d[i, 0], embeddings_2d[i, 1], word,
                        fontsize=10,
                        bbox=dict(boxstyle='round,pad=0.3', fc='yellow', alpha=0.5))
            texts.append(txt)

        adjust_text(texts, 
                    arrowprops=dict(arrowstyle='->', color='gray', lw=0.5),
                    expand_points=(1.5, 1.5))

        plt.title('Word2Vec Word Relationships Map', fontsize=16)
        plt.xlabel('Dimension 1')
        plt.ylabel('Dimension 2')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(args.output, dpi=300, bbox_inches='tight')
        print(f"Plot saved to {args.output}")

        return 0
    except Exception as e:
        print(f"Ошибка: {e}")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())