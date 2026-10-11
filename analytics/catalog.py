"""
Каталог технологий для интерфейса: отображаемое имя, синонимы для поиска и категории.

Ключи совпадают с analytics.embeddings.patterns.PATTERNS и таблицей tech. Синонимы — то, что
пользователь может набрать в поиске (не регулярные выражения: их роль — в patterns.py).
"""
from dataclasses import dataclass, field

from utils.groups import categories as GROUPS

# Широкие пересекающиеся группы из utils.groups показываются как «области», остальные — как категории
AREA_GROUPS = ("web", "mobile", "data_science", "ai", "infrastructure")

GROUP_NAMES = {
    "programming_language": "Язык программирования",
    "operating_system": "Операционная система",
    "containerization": "Контейнеризация",
    "version_control_system": "Система контроля версий",
    "code_hosting_platform": "Хостинг кода",
    "ml_llm": "Языковая модель (LLM)",
    "ml_multimodal": "Мультимодальная модель",
    "ml_image_generation": "Генерация изображений",
    "ml_speech": "Распознавание речи",
    "ml_vision": "Компьютерное зрение",
    "ml_nlp_encoders": "NLP-энкодер",
    "ml_nlp_seq2seq": "NLP seq2seq",
    "database_sql_relational": "Реляционная СУБД",
    "database_cloud_data_warehouse": "Облачное хранилище данных",
    "database_embedded_analytical": "Встраиваемая аналитическая СУБД",
    "database_olap_columnar": "Колоночная OLAP-СУБД",
    "database_document": "Документная СУБД",
    "database_multi_model": "Мультимодельная СУБД",
    "database_wide_column": "Wide-column СУБД",
    "database_key_value_cache": "Key-value хранилище / кэш",
    "database_distributed_kv": "Распределённое key-value хранилище",
    "database_search": "Поисковый движок",
    "database_graph": "Графовая СУБД",
    "database_time_series": "СУБД временных рядов",
    "database_distributed_sql": "Распределённая SQL-СУБД",
    "sql_query_engine": "SQL-движок запросов",
    "database_embedded_kv": "Встраиваемое key-value хранилище",
    "big_data_sql_on_hadoop": "SQL поверх Hadoop",
    "web": "Веб",
    "mobile": "Мобильная разработка",
    "data_science": "Data Science",
    "ai": "ИИ",
    "infrastructure": "Инфраструктура",
}

# key: (отображаемое имя, синонимы для поиска)
_CATALOG: dict[str, tuple[str, list[str]]] = {
    # Языки программирования
    "python": ("Python", ["py", "cpython", "pypy", "pytest", "pip", "poetry"]),
    "java": ("Java", ["jvm", "jdk", "jre", "spring boot"]),
    "javascript": ("JavaScript", ["js", "node", "node.js", "nodejs", "deno", "npm", "yarn", "vue", "next.js"]),
    "typescript": ("TypeScript", ["ts", "tsconfig", "ts-node"]),
    "rust": ("Rust", ["cargo", "crates.io", "rustlang"]),
    "go": ("Go", ["golang", "goroutine"]),
    "ruby": ("Ruby", ["rails", "ruby on rails", "rubygems", "bundler"]),
    "php": ("PHP", ["laravel", "composer"]),
    "csharp": ("C#", ["c sharp", "csharp", ".net", "dotnet", "asp.net"]),
    "cpp": ("C++", ["cpp", "cplusplus", "cxx"]),
    "c": ("C", ["c language", "c11", "c99", "gcc", "clang", "libc"]),
    "kotlin": ("Kotlin", ["ktor", "kotlinx"]),
    "swift": ("Swift", ["swiftui", "xcode"]),
    "scala": ("Scala", ["sbt", "akka"]),
    "haskell": ("Haskell", ["ghc", "cabal"]),
    "elixir": ("Elixir", ["phoenix", "beam"]),
    "erlang": ("Erlang", ["otp", "beam"]),
    "dart": ("Dart", ["flutter"]),
    "julia": ("Julia", ["julialang", "juliacon"]),
    "matlab": ("MATLAB", ["octave", "gnu octave"]),
    "shell": ("Shell", ["bash", "zsh", "fish", "sh", "shell script"]),
    "r": ("R", ["rstudio", "tidyverse", "ggplot2", "cran", "dplyr", "shiny"]),
    # Операционные системы и инфраструктура
    "linux": ("Linux", ["ubuntu", "debian", "fedora", "arch linux", "centos", "rhel", "nixos", "gentoo"]),
    "windows": ("Windows", ["win11", "win10", "wsl", "windows server"]),
    "macos": ("macOS", ["mac os", "os x", "osx"]),
    "ios": ("iOS", ["ipados", "watchos", "tvos", "iphone"]),
    "android": ("Android", []),
    "chromeos": ("ChromeOS", ["chrome os", "chromebook"]),
    "bsd": ("BSD", ["freebsd", "openbsd", "netbsd", "dragonfly bsd"]),
    "solaris": ("Solaris", ["illumos"]),
    "openwrt": ("OpenWrt", []),
    "fuchsia": ("Fuchsia", []),
    "docker": ("Docker", ["containers", "dockerfile"]),
    # Контроль версий и хостинг кода
    "git": ("Git", ["git lfs", "git flow"]),
    "github": ("GitHub", ["gh"]),
    "gitlab": ("GitLab", []),
    "bitbucket": ("Bitbucket", []),
    "mercurial": ("Mercurial", ["hg"]),
    "svn": ("Subversion", ["svn"]),
    "perforce": ("Perforce", ["helix core", "p4v"]),
    "bazaar": ("Bazaar", ["bzr"]),
    "fossil": ("Fossil", ["fossil scm"]),
    # LLM и генеративные модели
    "gpt": ("ChatGPT / GPT", ["chatgpt", "gpt-4", "gpt4", "gpt-4o", "gpt-3.5", "openai"]),
    "claude": ("Claude", ["anthropic", "claude sonnet", "claude opus", "claude haiku"]),
    "gemini": ("Gemini", ["google gemini", "gemini pro"]),
    "llama": ("Llama", ["llama 3", "llama 2", "code llama", "llama.cpp", "meta llama"]),
    "mistral": ("Mistral", ["mistral 7b", "mistral ai"]),
    "mixtral": ("Mixtral", ["mixtral 8x7b"]),
    "qwen": ("Qwen", ["qwen2", "qwen coder"]),
    "yi": ("Yi", ["yi-34b"]),
    "phi": ("Phi", ["phi-3", "phi-2"]),
    "gemma": ("Gemma", ["gemma 2", "codegemma"]),
    "deepseek": ("DeepSeek", ["deepseek coder"]),
    "dbrx": ("DBRX", ["databricks dbrx"]),
    "starcoder": ("StarCoder", ["starcoder2"]),
    "gpt_neo_family": ("GPT-Neo / GPT-J / GPT-2", ["gpt-neo", "gpt-neox", "gpt-j", "gpt-2", "gpt2"]),
    "falcon": ("Falcon", ["falcon 40b", "falcon 180b"]),
    "bloom": ("BLOOM", ["bloomz", "bigscience"]),
    "rwkv": ("RWKV", []),
    "vicuna": ("Vicuna", []),
    "alpaca": ("Alpaca", ["stanford alpaca"]),
    "guanaco": ("Guanaco", []),
    "wizardlm": ("WizardLM", ["wizardcoder"]),
    "llava": ("LLaVA", []),
    "clip": ("CLIP", ["openai clip"]),
    "whisper": ("Whisper", ["openai whisper", "whisper.cpp", "whisperx"]),
    "sam": ("Segment Anything (SAM)", ["segment anything", "sam 2"]),
    "bert_family": ("BERT и производные", ["bert", "roberta", "distilbert", "albert", "electra"]),
    "t5": ("T5", ["flan-t5", "mt5"]),
    "bart": ("BART", []),
    "dalle": ("DALL·E", ["dall-e", "dalle", "dall-e 3"]),
    "stable_diffusion": ("Stable Diffusion", ["sdxl", "comfyui", "automatic1111"]),
    "midjourney": ("Midjourney", []),
    "imagen": ("Imagen", ["google imagen"]),
    "kandinsky": ("Kandinsky", []),
    # Реляционные и облачные хранилища
    "postgresql": ("PostgreSQL", ["postgres", "psql", "pg", "pgvector", "psycopg"]),
    "mysql": ("MySQL", ["innodb"]),
    "mariadb": ("MariaDB", []),
    "sqlite": ("SQLite", ["sqlite3"]),
    "oracle": ("Oracle Database", ["oracle"]),
    "sqlserver": ("SQL Server", ["mssql", "ms sql", "t-sql", "tsql", "ssms"]),
    "firebird": ("Firebird", []),
    "db2": ("Db2", ["ibm db2"]),
    "snowflake": ("Snowflake", ["snowpark"]),
    "redshift": ("Amazon Redshift", ["redshift", "aws redshift"]),
    "bigquery": ("BigQuery", ["google bigquery"]),
    # Аналитические и колоночные
    "duckdb": ("DuckDB", []),
    "clickhouse": ("ClickHouse", []),
    "vertica": ("Vertica", []),
    "greenplum": ("Greenplum", []),
    "pinot": ("Apache Pinot", ["pinot"]),
    "druid": ("Apache Druid", ["druid"]),
    "trino": ("Trino", []),
    "presto": ("Presto", ["prestodb"]),
    "hive": ("Apache Hive", ["hive", "hiveql"]),
    # NoSQL
    "mongodb": ("MongoDB", ["mongo"]),
    "cassandra": ("Cassandra", ["apache cassandra", "cql"]),
    "scylladb": ("ScyllaDB", ["scylla"]),
    "hbase": ("HBase", ["apache hbase"]),
    "redis": ("Redis", ["redis-cli"]),
    "valkey": ("Valkey", []),
    "memcached": ("Memcached", []),
    "aerospike": ("Aerospike", []),
    "foundationdb": ("FoundationDB", []),
    "rocksdb": ("RocksDB", []),
    "leveldb": ("LevelDB", []),
    "lmdb": ("LMDB", []),
    "arangodb": ("ArangoDB", []),
    "neo4j": ("Neo4j", ["cypher"]),
    "dgraph": ("Dgraph", []),
    "janusgraph": ("JanusGraph", []),
    # Поиск и временные ряды
    "elasticsearch": ("Elasticsearch", ["elastic", "elastic stack"]),
    "opensearch": ("OpenSearch", []),
    "solr": ("Apache Solr", ["solr"]),
    "influxdb": ("InfluxDB", ["influxql"]),
    "timescaledb": ("TimescaleDB", ["timescale"]),
    "questdb": ("QuestDB", []),
    "victoriametrics": ("VictoriaMetrics", []),
    # Распределённые SQL
    "cockroachdb": ("CockroachDB", ["cockroach"]),
    "tidb": ("TiDB", ["tikv"]),
    "yugabytedb": ("YugabyteDB", ["yugabyte"]),
}


@dataclass(frozen=True)
class TechInfo:
    key: str
    name: str
    aliases: tuple[str, ...]
    categories: tuple[str, ...] = field(default=())  # узкие группы из utils.groups
    areas: tuple[str, ...] = field(default=())       # широкие группы (web, ai, ...)


def _build() -> dict[str, TechInfo]:
    catalog = {}
    for key, (name, aliases) in _CATALOG.items():
        groups = [g for g, members in GROUPS.items() if key in members]
        catalog[key] = TechInfo(
            key=key,
            name=name,
            aliases=tuple(aliases),
            categories=tuple(g for g in groups if g not in AREA_GROUPS),
            areas=tuple(g for g in groups if g in AREA_GROUPS),
        )
    return catalog


CATALOG: dict[str, TechInfo] = _build()


def tech_info(key: str) -> TechInfo:
    """Описание технологии; для неизвестного ключа — сам ключ как имя (например, если PATTERNS расширили)."""
    return CATALOG.get(key) or TechInfo(key=key, name=key, aliases=())
