import argparse
from pathlib import Path
import csv
import json
from db import session_scope
from db.queries import iter_tech_names

def parse_args():
    p = argparse.ArgumentParser(
        prog="export_titles",
        description="Выгрузка технологий Tech из БД в файл (txt/csv/jsonl)"
    )
    p.add_argument("-d", "--db", required=True, help="DB URL (например, sqlite:///hn.db)")
    p.add_argument("-o", "--out", required=True, help="Путь к выходному файлу (например, samples/titles.txt)")
    p.add_argument("--format", choices=["txt", "csv", "jsonl"], default="txt", help="Формат выхода (по умолчанию txt)")
    p.add_argument("--limit", type=int, default=None, help="Ограничение числа записей")
    return p.parse_args()

def main() -> int:
    args = parse_args()
    try:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        with session_scope(args.db) as session:
            rows = iter_tech_names(session, limit=args.limit)

            if args.format == "txt":
                with open(out_path, "w", encoding="utf-8") as f:
                    for _, name in rows:
                        f.write(name + "\n")

            elif args.format == "csv":
                with open(out_path, "w", encoding="utf-8", newline="") as f:
                    w = csv.writer(f)
                    w.writerow(["id", "name"])
                    for _id, name in rows:
                        w.writerow([_id, name])

            else:  # jsonl
                with open(out_path, "w", encoding="utf-8") as f:
                    for _id, name in rows:
                        f.write(json.dumps({"id": _id, "name": name}, ensure_ascii=False) + "\n")

        print(f"Готово: экспорт технологий в {out_path}")
        return 0
    except Exception as e:
        print(f"Ошибка: {e}")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
