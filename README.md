## Содержание

- [Установка зависимостей](#установка-зависимостей)
- [Быстрый старт](#быстрый-старт)
- [Скрипты](#скрипты)
  - [Скрипты основной директории](#скрипты-основной-директории)
    - [scripts.retrieve](#scriptsretrieve)
    - [scripts.create_samples](#scriptscreate_samples)
  - [Скрипты для работы с базой данных](#скрипты-для-работы-с-базой-данных)
    - [db.scripts.ingest](#dbscriptsingest)
    - [db.scripts.export_titles](#dbscriptsexport_titles)
    - [db.scripts.export_tech_names](#dbscriptsexport_tech_names)
    - [db.scripts.export_context](#dbscriptsexport_context)
  - [Скрипты для выполнения анализа](#скрипты-для-выполнения-анализа)
    - [analytics.embeddings.scripts.classify_tech](#analyticsembeddingsscriptsclassify_tech)
    - [analytics.embeddings.scripts.build_rel_matrix](#analyticsembeddingsscriptsbuild_rel_matrix)
    - [analytics.embeddings.scripts.lemmatize](#analyticsembeddingsscriptslemmatize)
    - [analytics.embeddings.scripts.sentences_to_vectors](#analyticsembeddingsscriptssentences_to_vectors)
    - [analytics.embeddings.scripts.train_model](#analyticsembeddingsscriptstrain_model)

  - [Скрипты для визуализации](#скрипты-для-визуализации)
    - [visualization.draw_relationship_map](#visualizationdraw_relationship_map)


## Установка зависимостей

    pip install -r requirements.txt.
    pip install spacy
    python -m spacy download en_core_web_sm

## Быстрый старт

Ниже — минимальный конвейер от загрузки данных до привязки технологий к статьям. Используются скрипты: retrieve, ingest, export_titles, sentences_to_vectors, classify_tech.

Предварительно:

Установите зависимости: 

    pip install -r requirements.txt.
    pip install spacy
    python -m spacy download en_core_web_sm

Скачиваем диапазон items и сохраняем в файл JSONL.GZ

    python3 -m scripts.retrieve \
    -o raw_data/hn_data.jsonl.gz \
    -s 38000000 -e 38010000 \
    -w 32 --progress-every 10000

Импортируйте истории и комментарии в БД (db.scripts.ingest)

    python3 -m db.scripts.ingest \
    -d sqlite:///hn.db \
    -i raw_data/hn_data.jsonl.gz \
    -b 1000

Выгрузите заголовки и комментарии историй в TXT (db.scripts.export_context)
Сразу сохраняем в путь, который ожидает embedder

    python3 -m db.scripts.export_context \
    -d sqlite:///hn.db \
    -o artifacts/sentences/context.txt \
    --format txt


Лемматизируйте заголовки (analytics.embeddings.scripts.lemmatize)
Преобразуем context.txt → context_lem.txt (леммы/токены по строкам)

    python3 -m analytics.embeddings.scripts.lemmatize \
    -i artifacts/sentences/context.txt \
    -o artifacts/sentences/context_lem.txt

Примечание:

Для лемматизации английских слов используется spaCy en_core_web_sm. Если не установлено:

    pip install spacy
    python -m spacy download en_core_web_sm

При необходимости можно отключить лемматизацию: добавьте флаг --no-lemmatize.

Преобразуйте предложения/леммы в токены для обучения/аналитики (analytics.embeddings.scripts.sentences_to_vectors)

Читает указанный TXT-файл (одна строка — один заголовок/список токенов) и формирует JSONL.GZ с токенами. Путь к входному файлу передаётся аргументом -i/--input.

    python3 -m analytics.embeddings.scripts.sentences_to_vectors \
    -i artifacts/sentences/context_lem.txt

Примечание: путь и имена выходных артефактов задаются реализацией класса TitleEmbedder (по умолчанию — в каталоге artifacts/embeddings/words).

## Скрипты
Все скрипты запускаются как модули из корневой папки проекта. Пример:

    python3 -m scripts.retrive

### Скрипты основной директории

##### scripts.retrieve

Скачивает элементы Hacker News (items) по диапазону ID и сохраняет в файл jsonl или jsonl.gz.

Аргументы:

    -o, --out PATH — путь к выходному файлу; по умолчанию raw_data/hn_data.jsonl.gz.
    -s, --start-id INT — начальный ID; если не указан, берется maxitem из API.
    -e, --end-id INT — конечный ID; если не указан вместе с start-id, используется 1.
    -w, --workers INT — количество потоков загрузки; по умолчанию 32.
    --no-compress — сохранить без gzip-компрессии (по умолчанию включена компрессия).
    -p, --progress-every INT — как часто выводить прогресс (в элементах); по умолчанию 10000.

##### scripts.create_samples

Создает демонстрационные наборы из большого файла jsonl/jsonl.gz. Каждый набор — отдельный файл (json или jsonl).

Аргументы:

    -i, --input PATH — путь к исходному файлу (jsonl/jsonl.gz) [обязательный].
    -o, --out-root PATH — папка для выходных файлов; по умолчанию samples.
    --sets NAME:COUNT [NAME:COUNT ...] — определения наборов (например, small_set_01:10 small_set_02:20) [обязательный].
    --filter-types TYPE [TYPE ...] — фильтр по типам элементов (например, story, comment).
    --seed INT — сид генератора случайных чисел; по умолчанию 42.
    --mode {random,head} — способ выборки: random (reservoir sampling) или head (первые K); по умолчанию random.
    --format {json,jsonl} — формат выходных файлов: json (массив) или jsonl (строка на объект); по умолчанию json.
    --no-pretty — не форматировать JSON (актуально для --format json).
    --keep-deleted — не отфильтровывать элементы с полями deleted/dead.

### Скрипты для работы с базой данных

##### db.scripts.ingest

Загружает истории и комментарии из jsonl/jsonl.gz в базу данных через HNHandler.

Аргументы:

    -d, --db DB_URL — строка подключения SQLAlchemy (например, sqlite:///hn.db, postgresql+psycopg://user:pass@host:5432/dbname) [обязательный].
    -i, --input PATH [PATH ...] — один или несколько файлов входных данных (jsonl/jsonl.gz) [обязательный].
    -b, --batch-size INT — размер пакетной вставки; по умолчанию 1000.
    --echo — включить вывод SQL-запросов SQLAlchemy.

#### db.scripts.export_titles

Выгружает заголовки историй (Story) из БД в файл формата txt, csv или jsonl.

Аргументы:

    -d, --db DB_URL — строка подключения SQLAlchemy (например, sqlite:///hn.db) [обязательный].
    -o, --out PATH — путь к выходному файлу (например, samples/titles.txt) [обязательный].
    --format {txt,csv,jsonl} — формат выгрузки; по умолчанию txt.
    --limit INT — ограничить количество выгружаемых записей; по умолчанию без ограничения.
    --keep-deleted — не фильтровать элементы с полями deleted/dead (по умолчанию фильтруются).

Примеры:

TXT: по одному заголовку на строку

    python3 -m db.scripts.export_titles -d sqlite:///hn.db -o samples/titles.txt --format txt

CSV: с заголовком "id,title"

    python3 -m db.scripts.export_titles -d sqlite:///hn.db -o samples/titles.csv --format csv

JSONL: одна строка — один объект {"id": ..., "title": "..."}

    python3 -m db.scripts.export_titles -d sqlite:///hn.db -o samples/titles.jsonl --format jsonl

Ограничение числа записей и сохранение deleted/dead

    python3 -m db.scripts.export_titles -d sqlite:///hn.db -o samples/titles.txt --limit 1000 --keep-deleted

Вывод:

    По завершении печатает путь к созданному файлу («Готово: экспорт заголовков в …»).
    При ошибке — текст ошибки.

Коды возврата:

    0 — выгрузка прошла успешно.
    1 — ошибка (например, недоступна БД, нет прав на запись файла).

#### db.scripts.export_tech_names

Выгружает список технологий из таблицы Tech в файл формата txt, csv или jsonl.

Аргументы:

    -d, --db DB_URL — строка подключения SQLAlchemy (например, sqlite:///hn.db) [обязательный].
    -o, --out PATH — путь к выходному файлу (например, tech_names.txt) [обязательный].
    --format {txt,csv,jsonl} — формат выгрузки; по умолчанию txt.
    --limit INT — ограничить количество выгружаемых записей; по умолчанию без ограничения.

Примеры:

TXT: по одному названию технологии на строку

    python3 -m db.scripts.export_tech_names -d sqlite:///hn.db -o tech_names.txt --format txt

CSV: с заголовком "id,name"

    python3 -m db.scripts.export_tech_names -d sqlite:///hn.db -o tech_names.csv --format csv --limit 100

JSONL: одна строка — один объект {"id": ..., "name": "..."}

    python3 -m db.scripts.export_tech_names -d sqlite:///hn.db -o tech_names.jsonl --format jsonl

Вывод:

    По завершении печатает путь к созданному файлу («Готово: экспорт технологий в …»).
    При ошибке — текст ошибки.

Коды возврата:

    0 — выгрузка прошла успешно.
    1 — ошибка (например, недоступна БД, нет таблицы tech).

#### db.scripts.export_context

Выгружает заголовки историй (Story) вместе с агрегированными комментариями (Comment) в файл формата txt, csv или jsonl.

Аргументы:

    -d, --db DB_URL — строка подключения SQLAlchemy (например, sqlite:///hn.db) [обязательный].
    -o, --out PATH — путь к выходному файлу (например, stories_with_context.txt) [обязательный].
    --format {txt,csv,jsonl} — формат выгрузки; по умолчанию txt.
    --limit INT — ограничить количество выгружаемых записей; по умолчанию без ограничения.
    --keep-deleted — не фильтровать элементы с полями deleted/dead (по умолчанию фильтруются).

Примеры:

TXT: заголовок + все комментарии в одной строке

    python3 -m db.scripts.export_context -d sqlite:///hn.db -o stories_context.txt --format txt

CSV: с заголовком "id,title,context"

    python3 -m db.scripts.export_context -d sqlite:///hn.db -o stories_context.csv --format csv --limit 5000

JSONL: одна строка — один объект {"id": ..., "title": "...", "context": "..."}

    python3 -m db.scripts.export_context -d sqlite:///hn.db -o stories_context.jsonl --format jsonl

Включая удалённые записи

    python3 -m db.scripts.export_context -d sqlite:///hn.db -o all_stories.txt --keep-deleted

Вывод:

    По завершении печатает путь к созданному файлу («Готово: экспорт заголовков и комментариев в …»).
    При ошибке — текст ошибки.

Коды возврата:

    0 — выгрузка прошла успешно.
    1 — ошибка (например, недоступна БД, нет таблиц stories/comments).

Замечания:

Текст автоматически очищается через функцию clean_text.
Batch-обработка по 10,000 записей для экономии памяти.
Комментарии агрегируются через SQL string_agg (PostgreSQL) или аналог для других СУБД.

### Скрипты для выполнения анализа

#### analytics.embeddings.scripts.classify_tech

Классифицирует статьи по технологиям на основе PATTERNS: добавляет недостающие технологии в таблицу Tech и создаёт связи многие-ко-многим между Story и Tech.

Аргументы:

    -d, --db DB_URL — строка подключения SQLAlchemy (например, sqlite:///hn.db) [обязательный].

Примеры:

    python3 -m analytics.embeddings.scripts.classify_tech -d sqlite:///hn.db
    python3 -m analytics.embeddings.scripts.classify_tech -d postgresql+psycopg://user:pass@host:5432/dbname

Вывод:

    Печатает количество обновлённых историй: «Обновлено историй: N».
    При ошибке — текст ошибки.

Коды возврата:

    0 — классификация завершена успешно.
    1 — ошибка (например, отсутствуют таблицы tech/stories или недоступна БД).

Замечания:

Ожидается, что таблицы stories, tech и таблица связи для Story.techs уже существуют.
Список технологий берётся из analytics.embeddings.patterns.PATTERNS. Убедитесь, что он импортируется корректно.

#### analytics.embeddings.scripts.build_rel_matrix

Строит матрицу косинусного сходства между технологиями на основе Word2Vec эмбеддингов. Принимает файл со списком технологий и обученную модель, выдаёт CSV-матрицу сходства.

Аргументы:

    -i, --input PATH — файл со списком технологий (одна на строку) [обязательный].
    -m, --model PATH — путь к обученной Word2Vec модели (.model) [обязательный].
    -o, --output PATH — путь к выходному CSV файлу с матрицей сходства [обязательный].

Примеры:

Построить матрицу сходства для списка технологий

    python3 -m analytics.embeddings.scripts.build_rel_matrix \
    -i tech_names.txt \
    -m artifacts/embeddings/words/w2v_tokens_300d.model \
    -o artifacts/similarity_matrix.csv

Вывод:

    Создаёт CSV-файл с матрицей сходства (строки и столбцы — названия технологий, значения — косинусное сходство от 0 до 1).
    При ошибке — текст ошибки.

Коды возврата:

    0 — матрица построена успешно.
    1 — ошибка (например, отсутствует модель, недостаточно токенов в словаре).

#### analytics.embeddings.scripts.lemmatize

Лемматизация/токенизация заголовков из TXT → TXT (по строкам). На вход — файл, где каждая строка это один заголовок. На выход — файл с леммами/токенами, разделёнными пробелами, по одной строке на исходный заголовок.

Аргументы:

    -i, --input PATH — путь к входному TXT (по одному заголовку на строку) [обязательный].
    -o, --output PATH — путь к выходному TXT (леммы по строкам) [обязательный].
    --keep-punct — оставлять знаки препинания как отдельные токены.
    --no-lemmatize — только токенизация, без лемматизации английских слов.
    --num-token STR — маркер для чисел (по умолчанию <NUM>; укажите None, чтобы оставлять числа как есть).
    --no-lower — не приводить к нижнему регистру перед лемматизацией.
    --preserve-words PATH — путь к файлу со словами, которые не нужно лемматизировать (по одному на строку).
    --add-preserve WORD [WORD ...] — дополнительные слова для защиты от лемматизации (через пробел).

Примеры:

Базовая лемматизация англ. слов, числа → <NUM>

    python3 -m analytics.embeddings.scripts.lemmatize -i samples/titles.txt -o artifacts/sentences/titles_lem.txt

Только токенизация, без лемм; оставить пунктуацию

    python3 -m analytics.embeddings.scripts.lemmatize -i samples/titles.txt -o artifacts/sentences/tokens.txt --no-lemmatize --keep-punct

Защита специфичных технических терминов

    python3 -m analytics.embeddings.scripts.lemmatize \
    -i samples/titles.txt \
    -o artifacts/sentences/titles_lem.txt \
    --add-preserve windows kubernetes c++

С файлом защищённых слов

    python3 -m analytics.embeddings.scripts.lemmatize \
    -i samples/titles.txt \
    -o artifacts/sentences/titles_lem.txt \
    --preserve-words preserve_words.txt

Числа не заменять: num-token=None

    python3 -m analytics.embeddings.scripts.lemmatize -i samples/titles.txt -o artifacts/sentences/titles_lem.txt --num-token None

Вывод:

    Создаёт указанный TXT-файл с результатами; каждая строка — токены/леммы исходного заголовка.
    Пустые строки сохраняются как пустые.
    Печатает количество защищённых слов и примеры.

Коды возврата:

    0 — успешно.
    1 — ошибка (например, отсутствует входной файл).

Примечание:

Для лемматизации английских слов используется модель spaCy en_core_web_sm. Установите заранее:
    pip install spacy
    python -m spacy download en_core_web_sm
Если spaCy недоступен, используйте --no-lemmatize.
Защищённые слова по умолчанию: windows, c++, kubernetes, jenkins, postgres, redis, aws, gcp, ios, macos.

#### analytics.embeddings.scripts.sentences_to_vectors

Преобразует файл предложений/лемм (TXT, одна строка — один заголовок/список токенов) в JSONL.GZ с токенами для обучения моделей. Обёртка над классом TitleEmbedder и его методом sentences_to_vectors.

Аргументы:

    -i, --input PATH — путь к входному TXT (например, artifacts/sentences/titles_lem.txt) [обязательный].

Примеры:

Генерировать токены из лемматизированных заголовков

    python3 -m analytics.embeddings.scripts.sentences_to_vectors \
    -i artifacts/sentences/titles_lem.txt

Вывод:

    Печатает «Готово: токены сгенерированы из …» по завершении.
    При ошибке — текст ошибки.

Коды возврата:

    0 — успешно.
    1 — ошибка (например, отсутствует входной файл).

Замечания:

Путь выходного файла и структура артефактов определяются реализацией TitleEmbedder. По умолчанию они размещаются в artifacts/embeddings/words.


#### analytics.embeddings.scripts.train_model

Тренирует модель Word2Vec по файлу токенов в формате JSONL.GZ (одна строка — список токенов). Сохраняет модель и текстовый формат в указанную директорию.

Аргументы:

    -p, --path PATH — путь к входному файлу JSONL.GZ с токенами [обязательный].
    -o, --out-dir DIR — директория для сохранения модели/векторов; по умолчанию artifacts/embeddings/words.
    --vector-size INT — размерность эмбеддингов; по умолчанию 300.
    --window INT — размер окна контекста; по умолчанию 5.
    --min-count INT — минимальная частота токена; по умолчанию 2.
    --sg {0,1} — архитектура: 0=CBOW, 1=Skip-gram; по умолчанию 1.
    --epochs INT — число эпох обучения; по умолчанию 5.
    --workers INT — число потоков; по умолчанию os.cpu_count().
    --aggregate-synonyms — агрегировать синонимы из patterns.py после обучения.

Примеры:

Обучить модель на файле токенов и сохранить артефакты

    python3 -m analytics.embeddings.scripts.train_model \
    -p artifacts/embeddings/words/titles.tokens.jsonl.gz \
    --vector-size 300 --window 5 --min-count 2 --epochs 5

Вывод:

    Сохраняет:
        файл модели w2v_<base>_<vector_size>d.model;
        текстовый формат w2v_<base>_<vector_size>d.txt
        в директории --out-dir.
    Печатает пути сохранённых файлов: «Сохранено: …».

Коды возврата:

    0 — обучение завершено успешно.
    1 — ошибка (например, отсутствует входной файл, проблемы с чтением JSONL.GZ).

Подсказка:

После обучения используйте model.wv.most_similar("token", topn=10) для поиска ближайших слов, и model.wv.similar_by_vector(vec) — для ближайших к произвольному вектору.

### Скрипты для визуализации

#### visualization.draw_relationship_map

Визуализирует 2D-карту технологических связей на основе матрицы сходства. Использует t-SNE для снижения размерности и автоматическое позиционирование меток для избежания перекрытий.

Аргументы:

    -m, --matrix PATH — путь к CSV-файлу с матрицей сходства [обязательный].
    -t, --tech PATH — файл со списком технологий для визуализации (одна на строку) [обязательный].
    -o, --output PATH — путь к выходному изображению (например, tech_map.png) [обязательный].

Примеры:

Построить карту отношений между технологиями

    python3 -m visualization.draw_relationship_map \
    -m artifacts/similarity_matrix.csv \
    -t tech_names.txt \
    -o tech_relationships_map.png

Вывод:

    Создаёт PNG-изображение с 2D-картой технологий.
    Печатает путь к сохранённому файлу.
    При ошибке — текст ошибки.

Коды возврата:

    0 — визуализация создана успешно.
    1 — ошибка (например, отсутствует матрица сходства, недостаточно технологий).

Замечания:

Использует t-SNE с perplexity=min(30, n-1) и random_state=42 для воспроизводимости.
Библиотека adjustText автоматически позиционирует метки и рисует стрелки к точкам.
Близкие на карте технологии семантически похожи (по эмбеддингам).
Размер изображения: 12×8 дюймов, DPI: 300.

![Relationship map](img/relationship_map.png "Result")
