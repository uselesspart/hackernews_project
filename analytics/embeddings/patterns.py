import re
from typing import List, Dict, Pattern

def _re(p: str) -> Pattern:
    return re.compile(p, re.IGNORECASE)

PATTERNS: Dict[str, List[Pattern]] = {
    "python": [
        _re(r"\bpython\b"), _re(r"\bcpython\b"), _re(r"\bpypy\b"), _re(r"\bpytest\b"),
        _re(r"\bpip3?\b"), _re(r"\bpoetry\b"), _re(r"\.py\b")
    ],
    "java": [
        _re(r"\bjava\b"), _re(r"\bjvm\b"), _re(r"\bjdk\b"), _re(r"\bjre\b"),
        _re(r"\bspring\s+boot\b")
    ],
    "javascript": [
        _re(r"\bjavascript\b"), _re(r"\bnode(?:\.?js)?\b"), _re(r"\bdeno\b"),
        _re(r"\bvue\.js\b"), _re(r"\bnext\.js\b"), _re(r"\bnpm\b"), _re(r"\byarn\b")
    ],
    "typescript": [
        _re(r"\btypescript\b"), _re(r"\btsconfig\b"), _re(r"\bts-node\b"), _re(r"\.ts\b")
    ],
    "rust": [
        _re(r"\brust\b"), _re(r"\bcargo\b"), _re(r"\bcrates?\.?io\b"), _re(r"\.rs\b"),
        _re(r"\bborrow\s+checker\b")
    ],
    "go": [
        _re(r"\bgolang\b"), _re(r"\bgoroutines?\b"), _re(r"\bgo\s+mod\b"),
        _re(r"\bgo\s+build\b"), _re(r"\bgo\s+1\.\d+\b"), _re(r"\.go\b"),
        _re(r"\bpackage\s+main\b"), _re(r"\bfunc\s+main\b")
    ],
    "ruby": [
        _re(r"\bruby\b"), _re(r"\brails\b"), _re(r"\bbundler\b"), _re(r"\brubygems\b"),
        _re(r"\.rb\b")
    ],
    "php": [
        _re(r"\bphp\b"), _re(r"\bcomposer\b"), _re(r"\blaravel\b"), _re(r"\.php\b")
    ],
    "csharp": [
        _re(r"\bC#\b"), _re(r"\bcsharp\b"), _re(r"\b\.?dotnet\b"), _re(r"\b\.NET\b")
    ],
    "cpp": [
        _re(r"\bC\+\+\b"), _re(r"\bc\+\+\d{2}\b"), _re(r"\bcpp\b"), _re(r"\bcxx\b"), _re(r"\bc++\b")
    ],
    "c": [
        _re(r"\bC(?:\s*language|11|17|99)\b"), _re(r"\blibc\b"), _re(r"\bclang\b"), _re(r"\bgcc\b")
    ],
    "kotlin": [
        _re(r"\bkotlin\b"), _re(r"\.kt\b"), _re(r"\.kts\b"), _re(r"\bkotlinx\b"), _re(r"\bktor\b")
    ],
    "swift": [
        _re(r"\bswiftui\b"), _re(r"\.swift\b"), _re(r"\bxcode\b"),
        _re(r"\bswift\s+(?:5|6|language)\b")
    ],
    "scala": [
        _re(r"\bscala\b"), _re(r"\.scala\b"), _re(r"\bsbt\b"), _re(r"\backa\b")
    ],
    "haskell": [
        _re(r"\bhaskell\b"), _re(r"\bghc\b"), _re(r"\bcabal\b"), _re(r"\bstack\b")
    ],
    "elixir": [
        _re(r"\belixir\b"), _re(r"\bphoenix\s+framework\b"), _re(r"\bmix\s+\w+"), _re(r"\bbeam\b")
    ],
    "erlang": [
        _re(r"\berlang\b"), _re(r"\botp\b"), _re(r"\bbeam\b")
    ],
    "dart": [
        _re(r"\bdart\b"), _re(r"\bflutter\b"), _re(r"\.dart\b")
    ],
    "julia": [
        _re(r"\bjulia\b"), _re(r"\.jl\b"), _re(r"\bjuliacon\b")
    ],
    "matlab": [
        _re(r"\bmatlab\b"), _re(r"\boctave\b")
    ],
    "shell": [
        _re(r"\bbash\b"), _re(r"\bzsh\b"), _re(r"\bfish\s+shell\b"),
        _re(r"\bshell\s+script\b"), _re(r"\.sh\b"), _re(r"\bposix\s+sh\b")
    ],
    "linux": [
        _re(r"\blinux\b"),
        _re(r"\bubuntu\b"), _re(r"\bdebian\b"), _re(r"\bfedora\b"), _re(r"\bcentos\b"),
        _re(r"\brhel\b"), _re(r"\balma\s*linux\b"), _re(r"\brocky\s*linux\b"),
        _re(r"\bopensuse\b"), _re(r"\bsles\b"),
        _re(r"\barch\b"), _re(r"\bmanjaro\b"), _re(r"\bmint\b"),
        _re(r"\bgentoo\b"), _re(r"\bnixos\b"),
        _re(r"\bkali\b"), _re(r"\braspbian\b"), _re(r"\braspberry\s*pi\s*os\b"),
    ],
    "docker": [
        _re(r"\bdocker\b")
    ],
    "r": [
        _re(r"\bRStudio\b"), _re(r"\btidyverse\b"), _re(r"\bggplot2\b"), _re(r"\bCRAN\b"),
        _re(r"\bdplyr\b"), _re(r"\bdata\.table\b"), _re(r"\bshiny\b"), _re(r"\.R\b")
    ],
    "gpt": [
        _re(r"\bchatgpt\b"),
        _re(r"\bgpt-?3\.5\b"),
        _re(r"\bgpt-?4(?:o(?:\.?mini)?|\.?1)?\b"),
        _re(r"\bopenai\s+(?:api|assistants?)\b"),
    ],
    "dalle": [
        _re(r"\bdall[-\s]?e(?:\s*\d)?\b"),
    ],
    "claude": [
        _re(r"\bclaude\s*(?:\d|3(?:\.5)?)?\b"),
        _re(r"\bclaude\s+(?:opus|sonnet|haiku)\b"),
        _re(r"\banthropic\b"),
    ],
    "gemini": [
        _re(r"\bgoogle\s+gemini\b"),
        _re(r"\bgemini\s+(?:1\.5|pro|ultra|flash)\b"),
    ],
    "llama": [
        _re(r"\bllama[-\s]?(?:2|3(?:\.\d)?)\b"),
        _re(r"\bcode[-\s]?llama\b"),
        _re(r"\bllama\.?cpp\b"),
    ],
    "mistral": [
        _re(r"\bmistral(?:[-\s]?(?:7b|nemo))?\b"),
        _re(r"\bmistralai\b"),
    ],
    "mixtral": [
        _re(r"\bmixtral(?:\s*8x7b)?\b"),
        _re(r"\bmixtral\s+of\s+experts\b"),
    ],
    "qwen": [
        _re(r"\bqwen(?:[-\s]?\d(?:\.\d)?)?(?:[-\s]?(?:vl|coder))?\b"),
    ],
    "yi": [
        _re(r"\byi[-\s]?(?:\d{1,3}b|coder)\b"),
    ],
    "phi": [
        _re(r"\bphi[-\s]?(?:2|3(?:\.5)?)(?:[-\s]?mini)?\b"),
    ],
    "gemma": [
        _re(r"\bgemma(?:[-\s]?2)?\b"),
        _re(r"\bcode[-\s]?gemma\b"),
    ],
    "deepseek": [
        _re(r"\bdeepseek(?:[-\s]?coder)?\b"),
    ],
    "dbrx": [
        _re(r"\bdbrx\b"),
    ],
    "starcoder": [
        _re(r"\bstarcoder(?:\s*2)?\b"),
    ],
    "whisper": [
        _re(r"\bopenai\s+whisper\b"),
        _re(r"\bwhisper\b"),
    ],
    "clip": [
        _re(r"\bopenai\s+clip\b"),
        _re(r"\bclip\s*(?:vit|model)\b"),
    ],
    "stable_diffusion": [
        _re(r"\bstable\s+diffusion\b"),
        _re(r"\bsd(?:xl|1\.\d|2\.\d)\b"),
        _re(r"\bautomatic1111\b"),
        _re(r"\bcomfyui\b"),
    ],
    "midjourney": [
        _re(r"\bmidjourney\b"),
    ],
    "imagen": [
        _re(r"\bgoogle\s+imagen\b"),
        _re(r"\bimagen\s*2\b"),
    ],
    "kandinsky": [
        _re(r"\bkandinsky\b"),
    ],
    "sam": [
        _re(r"\bsegment\s+anything\b"),
        _re(r"\bsam2?\b"),
    ],
    "bert_family": [
        _re(r"\bbert\b"),
        _re(r"\broberta\b"),
        _re(r"\balbert\b"),
        _re(r"\bdistilbert\b"),
        _re(r"\belectra\b"),
        _re(r"\bxlm[-\s]?roberta\b"),
    ],
    "t5": [
        _re(r"\bflan[-\s]?t5\b"),
        _re(r"\bmt5\b"),
        _re(r"\bt5\b"),
    ],
    "bart": [
        _re(r"\bbart\b"),
    ],
    "gpt_neo_family": [
        _re(r"\bgpt[-\s]?neo\b"),
        _re(r"\bgpt[-\s]?neox\b"),
        _re(r"\bgpt[-\s]?j\b"),
        _re(r"\bgpt-?2\b"),
    ],
    "falcon": [
        _re(r"\bfalcon[-\s]?(?:7b|40b|180b)\b"),
    ],
    "bloom": [
        _re(r"\bbloom(?:[-\s]?z)?\b"),
        _re(r"\bbigscience\b"),
    ],
    "rwkv": [
        _re(r"\brwkv\b"),
    ],
    "vicuna": [
        _re(r"\bvicuna\b"),
    ],
    "alpaca": [
        _re(r"\balpaca\b"),
    ],
    "guanaco": [
        _re(r"\bguanaco\b"),
    ],
    "wizardlm": [
        _re(r"\bwizard(?:lm|coder)\b"),
    ],
    "llava": [
        _re(r"\bllava\b"),
    ],
    "postgresql": [
        _re(r"\bpostgres(?:ql)?\b"),
        _re(r"\bpsql\b"),
        _re(r"\bpsycopg2?\b"),
        _re(r"\bpg_(?:dump|restore|ctl|bench|stat)\b"),
        _re(r"\btimescaledb\b"),
        _re(r"\bpgvector\b"),
    ],
    "mysql": [
        _re(r"\bmysql\b"),
        _re(r"\bmysqld\b"),
        _re(r"\binnodb\b"),
    ],
    "mariadb": [
        _re(r"\bmariadb\b"),
    ],
    "sqlite": [
        _re(r"\bsqlite(?:3)?\b"),
        _re(r"\.sqlite3?\b"),
    ],
    "oracle": [
        _re(r"\boracle\s+database\b"),
        _re(r"\boracle\b"),
    ],
    "sqlserver": [
        _re(r"\bsql\s*server\b"),
        _re(r"\bmssql\b"),
        _re(r"\bssms\b"),
        _re(r"\bt[-\s]?sql\b"),
    ],
    "snowflake": [
        _re(r"\bsnowflake\b"),
        _re(r"\bsnowpark\b"),
    ],
    "redshift": [
        _re(r"\baws\s+redshift\b"),
        _re(r"\bredshift\b"),
    ],
    "bigquery": [
        _re(r"\bbigquery\b"),
    ],
    "duckdb": [
        _re(r"\bduckdb\b"),
    ],
    "clickhouse": [
        _re(r"\bclickhouse\b"),
    ],
    "mongodb": [
        _re(r"\bmongodb\b"),
        _re(r"\bmongod\b"),
        _re(r"\bmongos\b"),
        _re(r"\bmongo\b"),
    ],
    "cassandra": [
        _re(r"\bcassandra\b"),
        _re(r"\bcql\b"),
    ],
    "scylladb": [
        _re(r"\bscylla(?:db)?\b"),
    ],
    "redis": [
        _re(r"\bredis\b"),
        _re(r"\bredis-cli\b"),
        _re(r"\bsentinel\b"),
    ],
    "valkey": [
        _re(r"\bvalkey\b"),
    ],
    "memcached": [
        _re(r"\bmemcached\b"),
    ],
    "elasticsearch": [
        _re(r"\belasticsearch\b"),
        _re(r"\belastic\s+stack\b"),
    ],
    "opensearch": [
        _re(r"\bopensearch\b"),
    ],
    "solr": [
        _re(r"\bsolr\b"),
    ],
    "neo4j": [
        _re(r"\bneo4j\b"),
        _re(r"\bcypher\b"),
    ],
    "arangodb": [
        _re(r"\barangodb\b"),
    ],
    "dgraph": [
        _re(r"\bdgraph\b"),
    ],
    "janusgraph": [
        _re(r"\bjanusgraph\b"),
    ],
    "hbase": [
        _re(r"\bhbase\b"),
    ],
    "hive": [
        _re(r"\bapache\s+hive\b"),
        _re(r"\bhive\b"),
    ],
    "aerospike": [
        _re(r"\baerospike\b"),
    ],
    "influxdb": [
        _re(r"\binfluxdb\b"),
        _re(r"\binflux\b"),
    ],
    "timescaledb": [
        _re(r"\btimescaledb\b"),
    ],
    "questdb": [
        _re(r"\bquestdb\b"),
    ],
    "victoriametrics": [
        _re(r"\bvictoriametrics\b"),
    ],
    "pinot": [
        _re(r"\bapache\s+pinot\b"),
        _re(r"\bpinot\b"),
    ],
    "druid": [
        _re(r"\bapache\s+druid\b"),
        _re(r"\bdruid\b"),
    ],
    "trino": [
        _re(r"\btrino\b"),
    ],
    "presto": [
        _re(r"\bpresto\b"),
    ],
    "cockroachdb": [
        _re(r"\bcockroachdb\b"),
        _re(r"\bcockroach\b"),
    ],
    "tidb": [
        _re(r"\btidb\b"),
        _re(r"\btikv\b"),
    ],
    "yugabytedb": [
        _re(r"\byugabyte(?:db)?\b"),
    ],
    "foundationdb": [
        _re(r"\bfoundationdb\b"),
    ],
    "rocksdb": [
        _re(r"\brocksdb\b"),
    ],
    "leveldb": [
        _re(r"\bleveldb\b"),
    ],
    "lmdb": [
        _re(r"\blmdb\b"),
    ],
    "firebird": [
        _re(r"\bfirebird\b"),
    ],
    "db2": [
        _re(r"\bdb2\b"),
        _re(r"\bibm\s*db2\b"),
    ],
    "vertica": [
        _re(r"\bvertica\b"),
    ],
    "greenplum": [
        _re(r"\bgreenplum\b"),
    ],
    "git": [
        _re(r"\bgit\b"),
        _re(r"\bgit[-\s]?(?:lfs|flow)\b"),
    ],
    "github": [
        _re(r"\bgithub\b"),
        _re(r"\bgh\s+cli\b"),
    ],
    "gitlab": [
        _re(r"\bgitlab\b"),
    ],
    "bitbucket": [
        _re(r"\bbitbucket\b"),
    ],
    "mercurial": [
        _re(r"\bmercurial\b"),
        _re(r"\bhg\b"),
    ],
    "svn": [
        _re(r"\bsubversion\b"),
        _re(r"\bsvn\b"),
    ],
    "perforce": [
        _re(r"\bperforce\b"),
        _re(r"\bp4\b"),
        _re(r"\bhelix\s+core\b"),
    ],
    "bazaar": [
        _re(r"\bbazaar\b"),
        _re(r"\bbzr\b"),
    ],
    "fossil": [
        _re(r"\bfossil\s+scm\b"),
        _re(r"\bfossil\b"),
    ],
    "windows": [
        _re(r"\bwindows\b"),
        _re(r"\bwin(?:dows)?\s*(?:7|8\.1|10|11)\b"),
        _re(r"\bwindows\s*server\s*(?:2012|2016|2019|2022)\b"),
        _re(r"\bwsl2?\b"),
    ],
    "macos": [
        _re(r"\bmacos\b"),
        _re(r"\bmac\s*os\b"),
        _re(r"\bos\s*x\b"),
        _re(r"\bdarwin\b"),
    ],
    "ios": [
        _re(r"\b(?:ios|ipados|watchos|tvos)\b"),
    ],
    "android": [
        _re(r"\bandroid\b"),
    ],
    "chromeos": [
        _re(r"\bchrome\s*os\b"),
        _re(r"\bchromebook\b"),
    ],
    "bsd": [
        _re(r"\bfreebsd\b"),
        _re(r"\bopenbsd\b"),
        _re(r"\bnetbsd\b"),
        _re(r"\bdragonfly\s*bsd\b"),
    ],
    "solaris": [
        _re(r"\bsolaris\b"),
        _re(r"\billumos\b"),
    ],
    "openwrt": [
        _re(r"\bopenwrt\b"),
    ],
    "fuchsia": [
        _re(r"\bfuchsia\b"),
    ],
}
