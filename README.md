### Установка зависимостей

    pip install -r requirements.txt

#### Скрипты
##### scripts/retrieve.py

Скачивает элементы Hacker News (items) по диапазону ID и сохраняет в файл jsonl или jsonl.gz.

Аргументы:

    -o, --out PATH — путь к выходному файлу; по умолчанию raw_data/hn_data.jsonl.gz.
    -s, --start-id INT — начальный ID; если не указан, берется maxitem из API.
    -e, --end-id INT — конечный ID; если не указан вместе с start-id, используется 1.
    -w, --workers INT — количество потоков загрузки; по умолчанию 32.
    --no-compress — сохранить без gzip-компрессии (по умолчанию включена компрессия).
    -p, --progress-every INT — как часто выводить прогресс (в элементах); по умолчанию 10000.

##### scripts/ingest.py

Загружает истории и комментарии из jsonl/jsonl.gz в базу данных через HNHandler.

Аргументы:

    -d, --db DB_URL — строка подключения SQLAlchemy (например, sqlite:///hn.db, postgresql+psycopg://user:pass@host:5432/dbname) [обязательный].
    -i, --input PATH [PATH ...] — один или несколько файлов входных данных (jsonl/jsonl.gz) [обязательный].
    -b, --batch-size INT — размер пакетной вставки; по умолчанию 1000.
    --echo — включить вывод SQL-запросов SQLAlchemy.

##### scripts/make_samples.py

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
