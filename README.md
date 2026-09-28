## Содержание

- [Установка зависимостей](#установка-зависимостей)
- [Тесты](#тесты)
- [Быстрый старт](#быстрый-старт)
- [API](#api)
- [Скрипты](#скрипты)
  - [Скрипты конвейера](#скрипты-конвейера)
  - [Скрипты основной директории](#скрипты-основной-директории)
    - [scripts.retrieve](#scriptsretrieve)
    - [scripts.combine](#scriptscombine)
    - [scripts.create_samples](#scriptscreate_samples)
  - [Скрипты для работы с базой данных](#скрипты-для-работы-с-базой-данных)
    - [db.scripts.ingest](#dbscriptsingest)
    - [db.scripts.db_connect](#dbscriptsdb_connect)
    - [db.scripts.trim](#dbscriptstrim)
    - [db.scripts.export_titles](#dbscriptsexport_titles)
    - [db.scripts.export_tech_names](#dbscriptsexport_tech_names)
    - [db.scripts.export_context](#dbscriptsexport_context)
    - [db.scripts.export_comments_for_techs](#dbscriptsexport_comments_for_techs)
    - [db.scripts.export_stories_meta](#dbscriptsexport_stories_meta)
  - [Скрипты для выполнения анализа](#скрипты-для-выполнения-анализа)
    - [analytics.embeddings.scripts.classify_tech](#analyticsembeddingsscriptsclassify_tech)
    - [analytics.embeddings.scripts.build_rel_matrix](#analyticsembeddingsscriptsbuild_rel_matrix)
    - [analytics.embeddings.scripts.lemmatize_file](#analyticsembeddingsscriptslemmatize_file)
    - [analytics.embeddings.scripts.sentences_to_vectors](#analyticsembeddingsscriptssentences_to_vectors)
    - [analytics.embeddings.scripts.train_model](#analyticsembeddingsscriptstrain_model)
    - [analytics.embeddings.scripts.calculate_irr](#analyticsembeddingsscriptscalculate_irr)
    - [analytics.embeddings.scripts.calculate_sentiment](#analyticsembeddingsscriptscalculate_sentiment)
    - [analytics.embeddings.scripts.precompute](#analyticsembeddingsscriptsprecompute)
  - [Скрипты для визуализации](#скрипты-для-визуализации)
    - [visualization.draw_relationship_map](#visualizationdraw_relationship_map)
    - [visualization.draw_wordcloud](#visualizationdraw_wordcloud)
    - [visualization.draw_irr_plot](#visualizationdraw_irr_plot)
    - [visualization.draw_sentiment_plot](#visualizationdraw_sentiment_plot)


## Установка зависимостей

Нужен Python 3.11 или новее (скрипты конвейера по умолчанию используют python3.12).

    pip install -r requirements.txt

В requirements.txt перечислены только прямые зависимости, включая модель spaCy en_core_web_sm (её версия согласована с версией spaCy).

## Тесты

Тесты лежат в tests/ и запускаются из корня проекта:

    pip install -r requirements-dev.txt
    python -m pytest
    python -m ruff check .

Настройки pytest и линтера ruff — в pyproject.toml.

Тесты не обращаются к сети и не требуют внешней БД: используются временные SQLite-базы, маленькие модели Word2Vec и подменённый HTTP-клиент.
Тесты, которым нужна модель spaCy en_core_web_sm, помечены маркером spacy и пропускаются, если модель не загружается (причина видна в выводе python -m pytest -rs). Запустить только их: python -m pytest -m spacy.

## Быстрый старт

Ниже — минимальный конвейер от загрузки данных до токенов для обучения модели. Используются скрипты: retrieve, ingest, export_context, lemmatize_file, sentences_to_vectors. Полный конвейер (с классификацией, обучением моделей и графиками) собран в scripts/bash и scripts/bat, см. [Скрипты конвейера](#скрипты-конвейера).

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

Выгрузите заголовки историй вместе с комментариями в TXT (db.scripts.export_context)

    python3 -m db.scripts.export_context \
    -d sqlite:///hn.db \
    -o artifacts/sentences/context.txt \
    --format txt

Лемматизируйте выгруженный текст (analytics.embeddings.scripts.lemmatize_file)
Преобразуем context.txt → context_lem.txt (леммы/токены по строкам)

    python3 -m analytics.embeddings.scripts.lemmatize_file \
    -i artifacts/sentences/context.txt \
    -o artifacts/sentences/context_lem.txt

Примечание:

Для лемматизации английских слов используется spaCy en_core_web_sm (ставится из requirements.txt). При необходимости лемматизацию можно отключить флагом --no-lemmatize.

Преобразуйте предложения/леммы в токены для обучения/аналитики (analytics.embeddings.scripts.sentences_to_vectors)

Читает указанный TXT-файл (одна строка — один заголовок/список токенов) и формирует JSONL.GZ с токенами. Пути к входному и выходному файлам передаются аргументами -i/--input и -o/--output.

    python3 -m analytics.embeddings.scripts.sentences_to_vectors \
    -i artifacts/sentences/context_lem.txt \
    -o artifacts/embeddings/words/context.tokens.jsonl.gz

## API

HTTP API на FastAPI для фронтенда (пакет api/). Отдаёт данные из БД: живые запросы (статьи, связи технологий, домены, динамика) и результаты предрасчёта (тональность, частые слова, соседи, координаты на карте, IRR).

Подготовка данных: после конвейера (ingest, classify_tech, обучение моделей) запустите [precompute](#analyticsembeddingsscriptsprecompute) или scripts/bash/precompute.sh (scripts\bat\precompute.bat). Без предрасчёта API работает, но метрики тональности, слов, соседей и IRR будут пустыми.

Запуск для разработки:

    set "HN_DB_URL=sqlite:///D:/hackernews_data/run_small/hn.db"
    uvicorn api.main:app --reload

    HN_DB_URL=sqlite:///hn.db uvicorn api.main:app --reload

Интерактивная документация (Swagger) — http://127.0.0.1:8000/docs, схема — /openapi.json.

Переменные окружения:

    HN_DB_URL — строка подключения SQLAlchemy; по умолчанию sqlite:///hn.db.
    HN_CORS_ORIGINS — адреса фронтенда через запятую; по умолчанию http://localhost:5173,http://localhost:3000.
    HN_MIN_SENTIMENT_COMMENTS — меньше скольких оценённых комментариев тональность помечается reliable=false; по умолчанию 30.
    HN_MIN_IRR_STORIES — меньше скольких статей IRR помечается reliable=false; по умолчанию 30.

Эндпоинты:

    GET /api/health — проверка, что сервис жив.
    GET /api/meta — сводка по выборке: число статей и комментариев, технологий с данными, период, время последнего предрасчёта.
    GET /api/techs/suggest?q=&limit=8 — подсказки для строки поиска: по имени, ключу и синонимам (golang → Go, postgres → PostgreSQL), с терпимостью к опечаткам. Пустой q — самые популярные технологии. В ответе matched — синоним, по которому найдено.
    GET /api/techs?sort=stories|comments|sentiment|irr|name&min_stories=1&limit=200 — технологии с метриками (для рейтингов и карты). При сортировке по sentiment и irr ненадёжные значения идут в конце.
    GET /api/techs/{key} — страница технологии: имя, синонимы, категории, статистика (статьи, комментарии, средний score, место, доля), тональность с примерами комментариев, IRR, семантические соседи, технологии из тех же статей, частые слова, домены ссылок, точка на карте. Неизвестный ключ — 404.
    GET /api/techs/{key}/stories?sort=score|comments|time&limit=20&offset=0 — статьи о технологии со ссылками на HN.
    GET /api/techs/{key}/timeline?bucket=day|week|month — число статей по периодам на общей оси всей выборки (пустые периоды — нули) и span_days — охват выборки.

Замечания:

У каждой метрики есть объём выборки (sentiment.n, stats.stories) и флаг reliable: фронтенд должен показывать ненадёжные значения как «мало данных», а не как результат.
Имена, синонимы и категории технологий задаются в analytics/catalog.py; список отслеживаемых технологий — в analytics/embeddings/patterns.py. Новую технологию нужно добавить в оба файла и в utils/groups.py.

## Скрипты
Все скрипты запускаются как модули из корневой папки проекта. Пример:

    python3 -m scripts.retrieve

Общее поведение:

- код возврата 0 — успех, 1 — ошибка (у отдельных скриптов есть свои коды, они указаны в описании), 130 — прерывание по Ctrl+C;
- сообщение об ошибке печатается в stderr в виде «Ошибка: ...»; чтобы увидеть полный traceback, задайте переменную окружения HN_DEBUG=1.

### Скрипты конвейера

scripts/bash/*.sh и scripts/bat/*.bat запускают этапы конвейера целиком:

    prepare — установка Python и зависимостей в venv, загрузка, импорт, классификация, выгрузка и лемматизация текстов историй с технологиями, обучение моделей заголовков и контекста, выгрузка и лемматизация комментариев по технологиям.
    precompute — предрасчёт данных для API (запускается после prepare).
    rel_map — матрица близости технологий и карта отношений.
    irr — метаданные статей, расчёт IRR и график.
    sentiment — сентимент-анализ комментариев (режим vader) и график.
    wordcloud — облако слов для первого файла из папки лемматизированных комментариев.

prepare создаёт venv (по умолчанию venv в корне проекта); остальные скрипты используют его, поэтому prepare запускается первым.
prepare не удаляет истории без технологий: они нужны как база сравнения для IRR («статьи про X получают в N раз больше комментариев, чем статьи без отслеживаемых технологий»). Для обучения моделей тексты выгружаются с флагом --with-techs-only.
Пути и параметры по умолчанию заданы в одном месте — scripts/bash/common.sh и scripts/bat/common.bat. Любой параметр можно переопределить переменной окружения:

    DB_URL=sqlite:///D:/hackernews_data/hn.db PLOTS_DIR=plots bash scripts/bash/irr.sh

    set "DB_URL=sqlite:///D:/hackernews_data/hn.db" && scripts\bat\irr.bat

Скрипты сами переходят в корень проекта (в релизной раскладке — в папку bin), поэтому их можно запускать из любой директории.
Графики сохраняются в PLOTS_DIR; по умолчанию это ../plots относительно корня проекта.

Вспомогательные скрипты scripts/lemmatize.sh и scripts/lemmatize.bat прогоняют все файлы папки через lemmatize_file:

    bash scripts/lemmatize.sh artifacts/tech_comments artifacts/tech

Для каждого файла name.ext создаётся OUTPUT_DIR/name_lem.ext; папка вывода по умолчанию — artifacts/tech.

### Скрипты основной директории

#### scripts.retrieve

Скачивает элементы Hacker News (items) по диапазону ID и сохраняет в файл jsonl или jsonl.gz.

Аргументы:

    -o, --out PATH — путь к выходному файлу; по умолчанию raw_data/hn_data.jsonl.gz. Папка создаётся автоматически.
    -s, --start-id INT — начальный ID; если не указан, берется maxitem из API.
    -e, --end-id INT — конечный ID; если не указан, используется 1. Диапазон можно задавать в обе стороны: при start-id > end-id ID перебираются по убыванию.
    -w, --workers INT — количество потоков загрузки; по умолчанию 32.
    --no-compress — сохранить без gzip-компрессии (по умолчанию включена компрессия).
    -p, --progress-every INT — как часто выводить прогресс (в элементах); по умолчанию 10000; 0 — не выводить.

Пример:

    python3 -m scripts.retrieve -o raw_data/hn_data.jsonl.gz -s 38000000 -e 38010000 -w 32

Вывод:

    Во время загрузки печатает прогресс: «[seen=…] saved=… errors=… elapsed=… rate=… items/s».
    По завершении — итог: «Готово: сохранено=… просмотрено=… ошибок=… время=… размер=… файл=…».
    Несуществующие ID (API возвращает null) пропускаются; при сетевых ошибках и ответах 429/5xx запрос повторяется до 3 раз, после чего элемент считается ошибкой.

Коды возврата:

    0 — загрузка завершена (даже если часть элементов не удалось скачать — см. errors в итоге).
    1 — ошибка (например, workers < 1, недоступен API при запросе maxitem).
    130 — остановлено пользователем (Ctrl+C).

#### scripts.combine

Склеивает несколько файлов *.jsonl.gz в один .jsonl.gz, удаляя дубликаты.

Аргументы:

    -i, --input_dir PATH — папка с исходными файлами [обязательный].
    -o, --output PATH — путь к выходному .jsonl.gz [обязательный].
    --pattern MASK — маска файлов; по умолчанию *.jsonl.gz.
    --recursive — искать файлы и во вложенных папках.
    --dedup {line,json} — как определять дубликаты: line — точное совпадение строки, json — совпадение JSON без учёта порядка ключей и пробелов; по умолчанию line.

Пример:

    python3 -m scripts.combine -i raw_data/parts -o raw_data/hn_data.jsonl.gz --dedup json

Вывод:

    Для каждого файла печатает число строк на входе, уникальных и дубликатов, в конце — общий итог.

Коды возврата:

    0 — склейка прошла успешно.
    1 — ошибка (например, в папке нет файлов по маске).

#### scripts.create_samples

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

Пример:

    python3 -m scripts.create_samples -i raw_data/hn_data.jsonl.gz --sets small_set_01:10 small_set_02:20

Вывод:

    Создаёт OUT_ROOT/NAME.json (или .jsonl) для каждого набора и печатает их список. Элементы в наборах не повторяются (дубликаты по id отбрасываются).

Коды возврата:

    0 — наборы созданы.
    1 — ошибка (например, неверный формат --sets или недостаточно элементов после фильтров).

### Скрипты для работы с базой данных

#### db.scripts.ingest

Загружает истории и комментарии из jsonl/jsonl.gz в базу данных через HNHandler.

Аргументы:

    -d, --db DB_URL — строка подключения SQLAlchemy (например, sqlite:///hn.db, postgresql+psycopg://user:pass@host:5432/dbname) [обязательный].
    -i, --input PATH [PATH ...] — один или несколько файлов входных данных (jsonl/jsonl.gz) [обязательный].
    -b, --batch-size INT — размер пакетной вставки; по умолчанию 1000.
    --echo — включить вывод SQL-запросов SQLAlchemy.

Пример:

    python3 -m db.scripts.ingest -d sqlite:///hn.db -i raw_data/hn_data.jsonl.gz -b 1000

Вывод:

    Для каждого файла печатает число загруженных историй и комментариев, в конце — общий итог.

Коды возврата:

    0 — импорт прошёл успешно.
    1 — ошибка (например, недоступна БД).
    2 — входной файл не найден.

Замечания:

Схема БД (таблицы и индексы) создаётся автоматически. Повторный импорт тех же элементов обновляет существующие записи (upsert по id).
Истории без заголовка и элементы других типов (job, poll) пропускаются.
Флаги HN dead/deleted сохраняются в таблицах story и comment; экспорт по умолчанию их отфильтровывает (см. --keep-deleted).
В БД, созданных до появления этих колонок, они добавляются автоматически при первом подключении и остаются пустыми (NULL = не помечено) до повторного импорта.
Индексы (comment.parent, story_tech.tech_id) тоже досоздаются автоматически; на большой существующей БД первое подключение может занять некоторое время.
Для SQLite включаются journal_mode=WAL и synchronous=NORMAL: рядом с файлом БД появятся файлы -wal и -shm, это нормально.

#### db.scripts.db_connect

Проверяет подключение к БД: печатает диалект, список таблиц и число записей в story, comment, tech и story_tech.

Аргументы:

    -d, --db DB_URL — строка подключения SQLAlchemy (например, sqlite:///hn.db) [обязательный].

Пример:

    python3 -m db.scripts.db_connect -d sqlite:///hn.db

Коды возврата:

    0 — подключение успешно.
    1 — ошибка подключения.

#### db.scripts.trim

Удаляет из БД истории, не связанные ни с одной технологией (запускается после classify_tech).
Конвейер prepare его больше не вызывает: без таких историй IRR сравнивает технологии не со «средней» статьёй, а со статьями о редких технологиях. Для обучения моделей используйте --with-techs-only в export_context и export_titles.

Аргументы:

    -d, --db DB_URL — строка подключения SQLAlchemy (например, sqlite:///hn.db) [обязательный].
    --dry-run — только показать число таких историй, ничего не удаляя.

Пример:

    python3 -m db.scripts.trim -d sqlite:///hn.db --dry-run

Вывод:

    «Удалено историй: N» или, с --dry-run, «Нашлось историй без технологий: N. Ничего не удалено (dry-run).»

Коды возврата:

    0 — успешно.
    1 — ошибка (например, недоступна БД).

Замечания:

Комментарии удалённых историй остаются в таблице comment.

#### db.scripts.export_titles

Выгружает заголовки историй (Story) из БД в файл формата txt, csv или jsonl.

Аргументы:

    -d, --db DB_URL — строка подключения SQLAlchemy (например, sqlite:///hn.db) [обязательный].
    -o, --out PATH — путь к выходному файлу (например, samples/titles.txt) [обязательный].
    --format {txt,csv,jsonl} — формат выгрузки; по умолчанию txt.
    --limit INT — ограничить количество выгружаемых записей; по умолчанию без ограничения.
    --keep-deleted — не фильтровать элементы с полями deleted/dead (по умолчанию фильтруются).
    --with-techs-only — выгружать только истории, связанные хотя бы с одной технологией (после classify_tech).

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
    1 — ошибка (например, недоступна БД).

Замечания:

Таблица tech заполняется скриптом classify_tech; до его запуска выгрузка будет пустой.

#### db.scripts.export_context

Выгружает заголовки историй (Story) вместе с агрегированными комментариями (Comment) в файл формата txt, csv или jsonl.

Аргументы:

    -d, --db DB_URL — строка подключения SQLAlchemy (например, sqlite:///hn.db) [обязательный].
    -o, --out PATH — путь к выходному файлу (например, stories_with_context.txt) [обязательный].
    --format {txt,csv,jsonl} — формат выгрузки; по умолчанию txt.
    --limit INT — ограничить количество выгружаемых историй; по умолчанию без ограничения.
    --keep-deleted — не фильтровать элементы с полями deleted/dead (по умолчанию фильтруются).
    --with-techs-only — выгружать только истории, связанные хотя бы с одной технологией (после classify_tech).

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
    1 — ошибка (например, недоступна БД, нет прав на запись файла).

Замечания:

Текст автоматически очищается через функцию clean_text (HTML-теги, markdown-ссылки и URL удаляются).
Строки читаются потоково пакетами по 10,000 для экономии памяти.
Агрегируются только комментарии верхнего уровня (прямые ответы на историю), в порядке их id.
Каждый комментарий очищается отдельно и склеивается в Python, поэтому результат детерминирован и не зависит от СУБД.

#### db.scripts.export_comments_for_techs

Выгружает все комментарии веток (включая ответы на ответы) к статьям о каждой технологии: отдельный txt на технологию или один comments.json.

Аргументы:

    -d, --db DB_URL — строка подключения SQLAlchemy (например, sqlite:///hn.db) [обязательный].
    -o, --output PATH — путь к выходной папке (например, artifacts/comments/) [обязательный].
    -m, --minimum INT — минимальное число статей о технологии для выгрузки комментариев; по умолчанию 100.
    -f, --filetype {txt,json} — формат выгрузки; по умолчанию txt.

Примеры:

    python3 -m db.scripts.export_comments_for_techs -d sqlite:///hn.db -o artifacts/comments/ -m 100

Один JSON-файл со всеми технологиями

    python3 -m db.scripts.export_comments_for_techs -d sqlite:///hn.db -o artifacts/comments/ -m 100 -f json

Вывод:

    txt: файл <технология>_<id>.txt на каждую технологию с комментариями, по одному комментарию на строку (технологии без комментариев пропускаются).
    json: файл comments.json — список объектов {"tech_id": ..., "tech": "...", "comments": [...]}.
    По завершении печатает путь к папке («Готово: экспорт комментариев в ...»).
    При ошибке — текст ошибки.

Коды возврата:

    0 — выгрузка прошла успешно.
    1 — ошибка (например, недоступна БД).

Замечания:

Комментарии помеченные dead/deleted, а также все комментарии к dead/deleted историям не выгружаются; ответы на dead-комментарий сохраняются.
Текст комментариев выгружается как есть (без clean_text); очистка и лемматизация — на следующем шаге (scripts/lemmatize.sh).

#### db.scripts.export_stories_meta

Выгружает метаданные для каждой статьи из БД в CSV.

Аргументы:

    -d, --db DB_URL — строка подключения SQLAlchemy (например, sqlite:///hn.db) [обязательный].
    -o, --output PATH — путь к выходному файлу (допускается также --out) [обязательный].

Примеры:

    python3 -m db.scripts.export_stories_meta -d sqlite:///hn.db -o artifacts/meta.csv

Вывод:

    CSV с колонками id, title, score, time, descendants, techs_count, tech_names (названия технологий через «|»), отсортированный по descendants по убыванию.
    По завершении печатает путь к созданному файлу («Готово: экспорт данных в ...»).
    При ошибке — текст ошибки.

Коды возврата:

    0 — выгрузка прошла успешно.
    1 — ошибка (например, недоступна БД).

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
    1 — ошибка (например, недоступна БД).

Замечания:

Список технологий и шаблонов берётся из analytics.embeddings.patterns.PATTERNS; недостающие таблицы создаются автоматически.
Скрипт только добавляет связи и никогда их не удаляет. После изменения шаблонов в patterns.py связи, найденные старыми шаблонами, останутся — надёжнее пересоздать БД (ingest + classify_tech).

#### analytics.embeddings.scripts.build_rel_matrix

Строит матрицу косинусного сходства между технологиями (или их группами) на основе Word2Vec эмбеддингов. Принимает файл со списком технологий и обученную модель, выдаёт CSV-матрицу.

Аргументы:

    -i, --input PATH — файл со списком технологий (одна на строку) [обязательный].
    -m, --model PATH — путь к обученной Word2Vec модели (.model) [обязательный].
    -o, --output PATH — путь к выходному CSV файлу с матрицей [обязательный].
    --groups — строить матрицу не по отдельным технологиям, а по группам из utils.groups.categories (вектор группы — среднее векторов её технологий).
    --min-group-size INT — минимум технологий из входа, попавших в группу, чтобы группа вошла в матрицу; по умолчанию 1.
    --distance — сохранять косинусное расстояние (1 - сходство) вместо сходства.

Примеры:

Построить матрицу сходства для списка технологий

    python3 -m analytics.embeddings.scripts.build_rel_matrix \
    -i artifacts/tech_names.txt \
    -m artifacts/embeddings/words/context/w2v_context_300d.model \
    -o artifacts/similarity_matrix.csv

Матрица по группам технологий

    python3 -m analytics.embeddings.scripts.build_rel_matrix \
    -i artifacts/tech_names.txt \
    -m artifacts/embeddings/words/context/w2v_context_300d.model \
    -o artifacts/groups_matrix.csv --groups

Вывод:

    Создаёт CSV-файл с матрицей (строки и столбцы — токены технологий или названия групп, значения — косинусное сходство от -1 до 1, на диагонали 1; с --distance — расстояние, на диагонали 0).
    С --groups печатает состав каждой группы: «[GROUP] имя: токены».
    При ошибке — текст ошибки.

Коды возврата:

    0 — матрица построена успешно.
    1 — ошибка (например, отсутствует модель, в словаре модели меньше 2 технологий из списка).

Замечания:

Технологии, которых нет в словаре модели, пропускаются. Названия приводятся к токенам модели: нижний регистр, пробелы заменяются на «_».

#### analytics.embeddings.scripts.lemmatize_file

Лемматизация/токенизация текста из TXT → TXT (по строкам). На вход — файл, где каждая строка это один заголовок или документ. На выход — файл с леммами/токенами, разделёнными пробелами, по одной строке на исходную строку.

Аргументы:

    -i, --input PATH — путь к входному TXT (по одному заголовку на строку) [обязательный].
    -o, --output PATH — путь к выходному TXT (леммы по строкам) [обязательный]. Папка должна существовать.
    --keep-punct — оставлять знаки препинания как отдельные токены.
    --no-lemmatize — только токенизация, без лемматизации английских слов.
    --num-token STR — маркер для чисел (по умолчанию <NUM>; укажите None, чтобы оставлять числа как есть).
    --no-lower — не приводить к нижнему регистру перед лемматизацией.
    --preserve-words PATH — путь к файлу со словами, которые не нужно лемматизировать (по одному на строку; строки с # — комментарии).
    --add-preserve WORD [WORD ...] — дополнительные слова для защиты от лемматизации (через пробел).

Примеры:

Базовая лемматизация англ. слов, числа → <NUM>

    python3 -m analytics.embeddings.scripts.lemmatize_file -i samples/titles.txt -o artifacts/sentences/titles_lem.txt

Только токенизация, без лемм; оставить пунктуацию

    python3 -m analytics.embeddings.scripts.lemmatize_file -i samples/titles.txt -o artifacts/sentences/tokens.txt --no-lemmatize --keep-punct

Защита специфичных технических терминов

    python3 -m analytics.embeddings.scripts.lemmatize_file \
    -i samples/titles.txt \
    -o artifacts/sentences/titles_lem.txt \
    --add-preserve pandas kubernetes jenkins

С файлом защищённых слов

    python3 -m analytics.embeddings.scripts.lemmatize_file \
    -i samples/titles.txt \
    -o artifacts/sentences/titles_lem.txt \
    --preserve-words preserve_words.txt

Числа не заменять: num-token=None

    python3 -m analytics.embeddings.scripts.lemmatize_file -i samples/titles.txt -o artifacts/sentences/titles_lem.txt --num-token None

Вывод:

    Создаёт указанный TXT-файл с результатами; каждая строка — токены/леммы исходной строки.
    Пустые строки входа пропускаются; строка без единого токена (например, только из знаков препинания) даёт пустую строку.
    Печатает количество защищённых слов (и примеры, если заданы --preserve-words или --add-preserve).

Коды возврата:

    0 — успешно.
    1 — ошибка (например, отсутствует входной файл или не загружается модель spaCy).

Примечание:

Перед токенизацией названия технологий со спецсимволами заменяются на канонические токены: C++ → cpp, C# → csharp, F# → fsharp, .NET → dotnet, Node.js → nodejs, Stable Diffusion → stable_diffusion, SQL Server → sqlserver. Эти токены не лемматизируются.
Сокращения раскрываются в леммы: don't → do not.

Для лемматизации английских слов используется модель spaCy en_core_web_sm (ставится из requirements.txt).
Если модель не загружается, скрипт завершается с ошибкой и указывает причину; чтобы работать без spaCy, используйте --no-lemmatize.
Защищённые слова по умолчанию: windows, kubernetes, jenkins, postgres, redis, aws, gcp, ios, macos и канонические токены технологий из примечания выше.

#### analytics.embeddings.scripts.sentences_to_vectors

Преобразует файл предложений/лемм (TXT, одна строка — один заголовок/список токенов) в JSONL.GZ с токенами для обучения моделей. Обёртка над функцией analytics.embeddings.title_embedder.save_token_matrix_jsonl_gz.

Аргументы:

    -i, --input PATH — путь к входному TXT (например, artifacts/sentences/titles_lem.txt) [обязательный].
    -o, --output PATH — путь к выходному JSONL.GZ [обязательный]. Папка создаётся автоматически.

Примеры:

Генерировать токены из лемматизированных заголовков

    python3 -m analytics.embeddings.scripts.sentences_to_vectors \
    -i artifacts/sentences/titles_lem.txt \
    -o artifacts/embeddings/words/titles.tokens.jsonl.gz

Вывод:

    Печатает «Сохранено N строк в …» и «Готово: токены сгенерированы из …» по завершении.
    При ошибке — текст ошибки.

Коды возврата:

    0 — успешно.
    1 — ошибка (например, отсутствует входной файл или не загружается модель spaCy).

Замечания:

Текст токенизируется и лемматизируется с теми же настройками, что и в lemmatize_file по умолчанию (нижний регистр, числа → <NUM>, без пунктуации), поэтому скрипту нужна модель spaCy. Для уже лемматизированного входа повторная лемматизация результат практически не меняет.

#### analytics.embeddings.scripts.train_model

Тренирует модель Word2Vec по файлу токенов в формате JSONL.GZ (одна строка — список токенов). Сохраняет модель и векторы в указанную директорию.

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
    -o artifacts/embeddings/words/titles \
    --vector-size 300 --window 5 --min-count 2 --epochs 5

Вывод:

    Сохраняет в директории --out-dir:
        файл модели w2v_<base>_<vector_size>d.model;
        векторы в текстовом формате word2vec w2v_<base>_<vector_size>d.txt;
        векторы в CSV w2v_<base>_<vector_size>d.csv;
        с --aggregate-synonyms — усреднённые (с весами по частоте) векторы технологий w2v_<base>_<vector_size>d.aggregated.csv и .aggregated.txt.
    <base> — имя входного файла без расширений: titles.tokens.jsonl.gz → titles.
    Печатает пути сохранённых файлов («Сохранено (…): …») и размер словаря.

Коды возврата:

    0 — обучение завершено успешно.
    1 — ошибка (например, отсутствует входной файл, проблемы с чтением JSONL.GZ).

Подсказка:

После обучения используйте model.wv.most_similar("token", topn=10) для поиска ближайших слов, и model.wv.similar_by_vector(vec) — для ближайших к произвольному вектору.

#### analytics.embeddings.scripts.calculate_irr

Рассчитывает IRR (incidence rate ratio) для каждой технологии: во сколько раз упоминание технологии в заголовке меняет ожидаемое число комментариев к статье.

Аргументы:

    -i, --input PATH — CSV с метаданными статей (результат export_stories_meta; используются колонки title и descendants) [обязательный]. Должен содержать и статьи без технологий: они — база сравнения.
    -m, --model PATH — путь Word2Vec модели, обученной на заголовках (.model) [обязательный].
    -o, --output PATH — путь к выходному CSV файлу с коэффициентами для технологий [обязательный].
    --family {negbin,poisson} — семейство GLM; по умолчанию negbin (отрицательная биномиальная, учитывает сверхдисперсию числа комментариев); poisson считается с робастными (HC0) ошибками.
    --groups — агрегировать технологии в группы из utils.groups.categories.
    --sample INT — случайная подвыборка N строк (для отладки).
    --max-rows INT — максимум строк; по умолчанию 500000.

Модель строится через statsmodels. Технологии извлекаются из заголовков по шаблонам patterns.py (не более трёх на заголовок). Признаки: has_<tech> для топ-50 технологий, has_pair_<a>__<b> для частых пар, sim_min/sim_mean (косинусная близость технологий в заголовке) и other_techs_count (число технологий вне топа). В топ попадают технологии и пары, встретившиеся не менее 5 раз. Постоянные и линейно зависимые признаки отбрасываются перед обучением (с сообщением в выводе).

Пример:

    python3 -m analytics.embeddings.scripts.calculate_irr \
    -i artifacts/meta.csv \
    -m artifacts/embeddings/words/titles/w2v_titles_300d.model \
    -o artifacts/coefs.csv

Вывод:

    Создаёт CSV с колонками feature, coef, se, pval, conf_low, conf_high, IRR, IRR_low, IRR_high (IRR = exp(coef), границы — 95% доверительный интервал).
    Печатает ход расчёта, оценку сверхдисперсии alpha (для negbin) и топ-10 признаков по IRR.
    При ошибке — текст ошибки.

Коды возврата:

    0 — рассчет произведен успешно.
    1 — ошибка (например, отсутствует модель или в заголовках не найдено ни одной технологии).

#### analytics.embeddings.scripts.calculate_sentiment

Рассчитывает эмоциональный отклик в комментариях к статьям о различных технологиях.

Аргументы:

    -i, --input PATH — путь к одному файлу (по одному комментарию в строке).
    -d, --dir PATH — папка с файлами для пакетной обработки.
    --pattern PATTERN — глоб-шаблон для выбора файлов в папке; по умолчанию *.txt.
    --recursive — рекурсивный проход по подпапкам.
    --titles-kv PATH — путь к модели Word2Vec (заголовки, .model); по умолчанию w2v_titles.model.
    --comments-kv PATH — путь к модели Word2Vec (заголовки+комментарии, .model); по умолчанию w2v_titles_comments.model.
    --mode {lexicon,vader,bootstrap} — режим анализа; по умолчанию lexicon.
    --keyword WORD — аспект/ключевое слово (опционально).
    --use-vader — сливать лексикон w2v с VADER.
    --p FLOAT — степень внимания к ключу; по умолчанию 2.0.
    --neg-window INT — окно для отрицаний; по умолчанию 3.
    --threshold FLOAT — порог меток {-1,0,1}; по умолчанию 0.12.
    --auto-thr — автокалибровка порога по распределению в файле.
    --auto-percent INT — процентиль |score| для автопорога; по умолчанию 60.
    --top-percent INT — топ-% уверенных примеров для bootstrap; по умолчанию 20.
    --out-csv PATH — итоговый CSV по всем обработанным файлам; по умолчанию corpus_summary.csv.
    --save-rows-dir PATH — папка для сохранения пофайловых TSV (idx, label, score/conf, text).

Нужно указать -i или -d.

Режимы:

    lexicon — оценка по лексикону: слова, близкие в модели комментариев к seed-словам good/bad и т.п. (с --use-vader — слитому с лексиконом VADER), с учётом отрицаний и усилителей.
    vader — оценка VADER (с --keyword — по окну вокруг ключевого слова).
    bootstrap — логистическая регрессия на векторах обеих моделей, обученная на самых уверенных метках lexicon; если уверенных меток меньше 50, используется lexicon (mode в итоге — lexicon_fallback).

Пример:

    python3 -m analytics.embeddings.scripts.calculate_sentiment \
    --dir artifacts/tech/ \
    --titles-kv artifacts/embeddings/words/titles/w2v_titles_300d.model \
    --comments-kv artifacts/embeddings/words/context/w2v_context_300d.model \
    --out-csv artifacts/corpus3.csv --mode bootstrap

Вывод:

    Создаёт CSV со сводкой по каждому файлу (технологии): число и доли положительных/отрицательных/нейтральных комментариев, polarity_ratio, sentiment_index и статистики оценок или уверенности.
    С --save-rows-dir — TSV с меткой и оценкой для каждого комментария.
    Ход обработки печатается в stderr.
    При ошибке — текст ошибки.

Коды возврата:

    0 — рассчет произведен успешно.
    1 — ошибка (например, отсутствует модель, не указаны -i/-d или в папке нет файлов по шаблону).

#### analytics.embeddings.scripts.precompute

Предрасчитывает данные для [API](#api) и сохраняет их в таблицы БД tech_metrics, tech_neighbor, tech_word и sentiment_example. Каждый запуск пересчитывает всё заново.

Аргументы:

    -d, --db DB_URL — строка подключения SQLAlchemy (например, sqlite:///hn.db) [обязательный].
    --context-model PATH — модель Word2Vec контекста (.model): семантические соседи и координаты на карте. Без неё не считаются.
    --titles-model PATH — модель Word2Vec заголовков (.model): IRR. Без неё не считается.
    --max-comments INT — максимум комментариев на технологию для тональности и частых слов (воспроизводимая случайная выборка); по умолчанию 5000.
    --top-words INT — сколько частых слов хранить на технологию; по умолчанию 100.
    --neighbors INT — сколько семантических соседей хранить; по умолчанию 10.
    --examples INT — сколько самых положительных и самых отрицательных комментариев хранить; по умолчанию 3.
    --threshold FLOAT — порог меток тональности; по умолчанию 0.12.
    --family {negbin,poisson} — семейство GLM для IRR; по умолчанию negbin.
    --no-lemmatize — считать частые слова без лемматизации (без spaCy).

Пример:

    python3 -m analytics.embeddings.scripts.precompute \
    -d sqlite:///hn.db \
    --context-model artifacts/embeddings/words/context/w2v_context_300d.model \
    --titles-model artifacts/embeddings/words/titles/w2v_titles_300d.model

Вывод:

    Для каждой технологии со статьями печатает число статей и комментариев в анализе, в конце — итог: «Готово: технологий N, соседей N, слов N, примеров N».

Коды возврата:

    0 — предрасчёт завершён.
    1 — ошибка (например, недоступна БД, отсутствует модель или не загружается spaCy без --no-lemmatize).

Замечания:

Статистика, тональность (VADER, как calculate_sentiment --mode vader) и слова считаются по комментариям всех веток статей о технологии, без dead/deleted.
IRR считается по всем живым статьям БД, поэтому БД не должна быть обрезана скриптом trim. Если IRR посчитать не удаётся (например, мало данных), он пропускается с сообщением, остальное сохраняется.
Пороги достоверности (сколько данных достаточно) применяет API, а не предрасчёт: в таблицах хранятся и значения, и объёмы выборок.


### Скрипты для визуализации

#### visualization.draw_relationship_map

Визуализирует 2D-карту технологических связей на основе матрицы сходства. Использует t-SNE для снижения размерности и автоматическое позиционирование меток для избежания перекрытий.

Аргументы:

    -m, --matrix PATH — путь к CSV-файлу с матрицей (сходства, расстояний или признаков) [обязательный].
    -t, --tech PATH — файл со списком технологий для визуализации (одна на строку); по умолчанию — все строки матрицы.
    -o, --output PATH — путь к выходному изображению (например, tech_map.png) [обязательный].
    --matrix-type {auto,features,similarity,distance} — тип входной матрицы; по умолчанию auto (определяется по диагонали: 1 — сходство, 0 — расстояние, неквадратная матрица — признаки).

Примеры:

Построить карту отношений между технологиями

    python3 -m visualization.draw_relationship_map \
    -m artifacts/similarity_matrix.csv \
    -t artifacts/tech_names.txt \
    -o tech_relationships_map.png

Вывод:

    Создаёт PNG-изображение с 2D-картой технологий.
    Печатает путь к сохранённому файлу.
    При ошибке — текст ошибки.

Коды возврата:

    0 — визуализация создана успешно.
    1 — ошибка (например, отсутствует матрица сходства, после фильтрации по -t осталось меньше 3 меток).

Замечания:

Использует t-SNE с perplexity=min(30, n-1) и random_state=42 для воспроизводимости.
Библиотека adjustText автоматически позиционирует метки и рисует стрелки к точкам.
Близкие на карте технологии семантически похожи (по эмбеддингам).
Размер изображения: 12×8 дюймов, DPI: 300.

![Relationship map](img/relationship_map.png "Result")

#### visualization.draw_wordcloud

Визуализирует облако слов для технологии по комментариям.

Аргументы:

    -i, --input PATH — путь к входному файлу (комментарии технологии, по одному на строку) [обязательный].
    -o, --output PATH — путь к выходному изображению [обязательный].
    --extra WORD — дополнительное слово, которое не нужно учитывать (обычно название самой технологии).

Примеры:

Построить облако слов по лемматизированным комментариям о Java

    python3 -m visualization.draw_wordcloud \
    -i artifacts/tech/java_2_lem.txt \
    -o artifacts/wordcloud.png \
    --extra java

Вывод:

    Создаёт PNG-изображение с облаком слов; заголовок — первая часть имени входного файла (java_2_lem.txt → java).
    Печатает путь к сохранённому файлу.
    При ошибке — текст ошибки.

Коды возврата:

    0 — визуализация создана успешно.
    1 — ошибка.

Замечания:

Английские стоп-слова и слова короче 3 символов не учитываются.

![Wordcloud](img/wordcloud.png "Result")

#### visualization.draw_irr_plot

Визуализирует чертеж, отражающий влияние технологий на число комментариев.

Аргументы:

    -i, --input PATH — CSV с коэффициентами (результат calculate_irr) [обязательный].
    -o, --output PATH — путь к выходному изображению [обязательный].

Примеры:

Построить график IRR по технологиям

    python3 -m visualization.draw_irr_plot \
    -i artifacts/coefs.csv \
    -o artifacts/irr.png

Вывод:

    Создаёт PNG-изображение с графиком: 20 технологий с наибольшим IRR (признаки has_<tech>, без пар) и их 95% доверительные интервалы; синим отмечены статистически значимые (интервал не включает 1).
    Печатает путь к сохранённому файлу.
    При ошибке — текст ошибки.

Коды возврата:

    0 — визуализация создана успешно.
    1 — ошибка.

![IRR](img/most_engaging_tech.png "Result")

#### visualization.draw_sentiment_plot

Визуализирует чертеж, отражающий результат сентимент анализа.

Аргументы:

    -i, --input PATH — путь к итоговому CSV (результат calculate_sentiment, например corpus_summary.csv) [обязательный].
    -o, --output PATH — путь к выходному изображению [обязательный].
    --sort-by COLUMN — колонка для сортировки (например, sentiment_index, polarity_ratio, mean_score); по умолчанию sentiment_index.
    --desc — сортировать по убыванию.

Пример:

    python3 -m visualization.draw_sentiment_plot \
    -i artifacts/corpus3.csv \
    -o artifacts/plots/sentiment.png

Вывод:

    Создаёт PNG-изображение со столбчатой диаграммой sentiment_index по технологиям.
    Печатает путь к сохранённому файлу.
    При ошибке — текст ошибки.

Коды возврата:

    0 — визуализация создана успешно.
    1 — ошибка (например, CSV пустой).

Замечания:

Если колонки --sort-by нет в CSV или она пустая, сортировка идёт по sentiment_index.

![Sentiment](img/sentiment.png "Result")
