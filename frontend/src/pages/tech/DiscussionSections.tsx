import type { TechProfile } from "../../api/types";
import { BarList } from "../../components/charts";
import { Section } from "../../components/ui";

const WORDS_SHOWN = 12;
const DOMAINS_SHOWN = 8;

export function WordsSection({ words }: { words: TechProfile["words"] }) {
  if (words.length === 0) return null;
  return (
    <Section id="words" title="О чём говорят" lead="Частые слова в комментариях, без служебных слов и самого названия.">
      <BarList
        label="Частые слова в комментариях"
        items={words.slice(0, WORDS_SHOWN).map((w) => ({ key: w.word, label: w.word, value: w.count }))}
      />
    </Section>
  );
}

export function DomainsSection({ domains }: { domains: TechProfile["domains"] }) {
  if (domains.length === 0) return null;
  return (
    <Section id="sources" title="Источники" lead="Сайты, на которые чаще всего ссылаются статьи.">
      <BarList
        label="Источники статей"
        items={domains.slice(0, DOMAINS_SHOWN).map((d) => ({ key: d.domain, label: d.domain, value: d.count }))}
      />
    </Section>
  );
}
