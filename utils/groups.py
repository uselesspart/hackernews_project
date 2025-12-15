categories = {
    # Core fine-grained categories
    "programming_language": [
        "python", "java", "javascript", "typescript", "rust", "go", "ruby", "php",
        "csharp", "cpp", "c", "kotlin", "swift", "scala", "haskell", "elixir",
        "erlang", "dart", "julia", "matlab", "shell", "r"
    ],

    "operating_system": [
        "linux", "windows", "macos", "ios", "android", "chromeos", "bsd",
        "solaris", "openwrt", "fuchsia"
    ],

    "containerization": ["docker"],

    "version_control_system": [
        "git", "mercurial", "svn", "perforce", "bazaar", "fossil"
    ],

    "code_hosting_platform": [
        "github", "gitlab", "bitbucket"
    ],

    "ml_llm": [
        "gpt", "claude", "gemini", "llama", "mistral", "mixtral", "qwen", "yi",
        "phi", "gemma", "deepseek", "dbrx", "starcoder", "gpt_neo_family",
        "falcon", "bloom", "rwkv", "vicuna", "alpaca", "guanaco", "wizardlm"
    ],

    "ml_multimodal": [
        "clip", "llava"
    ],

    "ml_image_generation": [
        "dalle", "stable_diffusion", "midjourney", "imagen", "kandinsky"
    ],

    "ml_speech": [
        "whisper"
    ],

    "ml_vision": [
        "sam"
    ],

    "ml_nlp_encoders": [
        "bert_family"
    ],

    "ml_nlp_seq2seq": [
        "t5", "bart"
    ],

    "database_sql_relational": [
        "postgresql", "mysql", "mariadb", "sqlite", "oracle", "sqlserver",
        "firebird", "db2"
    ],

    "database_cloud_data_warehouse": [
        "snowflake", "redshift", "bigquery"
    ],

    "database_embedded_analytical": [
        "duckdb"
    ],

    "database_olap_columnar": [
        "clickhouse", "vertica", "greenplum", "pinot", "druid"
    ],

    "database_document": [
        "mongodb"
    ],

    "database_multi_model": [
        "arangodb"
    ],

    "database_wide_column": [
        "cassandra", "scylladb", "hbase"
    ],

    "database_key_value_cache": [
        "redis", "valkey", "memcached"
    ],

    "database_distributed_kv": [
        "aerospike", "foundationdb"
    ],

    "database_search": [
        "elasticsearch", "opensearch", "solr"
    ],

    "database_graph": [
        "neo4j", "arangodb", "dgraph", "janusgraph"
    ],

    "database_time_series": [
        "influxdb", "timescaledb", "questdb", "victoriametrics"
    ],

    "database_distributed_sql": [
        "cockroachdb", "tidb", "yugabytedb"
    ],

    "sql_query_engine": [
        "trino", "presto"
    ],

    "database_embedded_kv": [
        "rocksdb", "leveldb", "lmdb"
    ],

    "big_data_sql_on_hadoop": [
        "hive"
    ],

    # Broad, overlapping categories requested
    "web": [
        # languages commonly used for web (frontend/backend/services)
        "javascript", "typescript", "python", "ruby", "php", "java", "go",
        "csharp", "rust", "scala", "kotlin", "dart",
        # storage, cache, search typical for web apps
        "postgresql", "mysql", "mariadb", "sqlite",
        "mongodb",
        "redis", "valkey", "memcached",
        "elasticsearch", "opensearch", "solr",
        # popular analytical/OLAP used alongside web backends
        "clickhouse"
    ],

    "mobile": [
        # platforms
        "android", "ios",
        # languages/tooling commonly used in mobile stacks
        "kotlin", "swift", "java", "dart",
        "javascript", "typescript", "csharp",
        "cpp", "c", "rust", "go"
    ],

    "data_science": [
        # primary languages
        "python", "r", "julia", "scala", "matlab",
        # warehouses and analytical engines
        "snowflake", "redshift", "bigquery",
        "duckdb", "clickhouse", "vertica", "greenplum",
        "trino", "presto", "hive",
        # time-series often used in analytics
        "influxdb", "timescaledb", "questdb", "victoriametrics",
        # optional relational store for analytics workloads
        "postgresql"
    ],

    "ai": [
        # LLMs and families
        "gpt", "claude", "gemini", "llama", "mistral", "mixtral", "qwen", "yi",
        "phi", "gemma", "deepseek", "dbrx", "starcoder",
        "gpt_neo_family", "falcon", "bloom", "rwkv",
        "vicuna", "alpaca", "guanaco", "wizardlm",
        # encoders and seq2seq
        "bert_family", "t5", "bart",
        # multimodal and perception
        "clip", "llava", "whisper", "sam",
        # image generation
        "dalle", "stable_diffusion", "midjourney", "imagen", "kandinsky",
        # languages often used for AI work
        "python", "r", "julia"
    ],

    "infrastructure": [
        # OS and shell
        "linux", "windows", "macos", "ios", "android", "chromeos", "bsd",
        "solaris", "openwrt", "fuchsia", "shell",
        # containers
        "docker",
        # VCS and hosting
        "git", "mercurial", "svn", "perforce", "bazaar", "fossil",
        "github", "gitlab", "bitbucket",
        # all databases, caches, search, query engines
        "postgresql", "mysql", "mariadb", "sqlite", "oracle", "sqlserver",
        "snowflake", "redshift", "bigquery", "duckdb", "clickhouse",
        "mongodb", "cassandra", "scylladb",
        "redis", "valkey", "memcached",
        "elasticsearch", "opensearch", "solr",
        "neo4j", "arangodb", "dgraph", "janusgraph",
        "hbase", "hive", "aerospike",
        "influxdb", "timescaledb", "questdb", "victoriametrics",
        "pinot", "druid",
        "trino", "presto",
        "cockroachdb", "tidb", "yugabytedb", "foundationdb",
        "rocksdb", "leveldb", "lmdb",
        "firebird", "db2", "vertica", "greenplum"
    ],
}