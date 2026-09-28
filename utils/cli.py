"""Общая обвязка для CLI-скриптов проекта."""
import functools
import os
import sys
import traceback
from collections.abc import Callable


def cli_main(func: Callable[[], int | None]) -> Callable[[], int]:
    """
    Оборачивает main() скрипта: любое исключение печатается в stderr как "Ошибка: ..."
    и превращается в код возврата 1. Полный traceback — при HN_DEBUG=1.
    Ctrl+C даёт код 130, как принято для прерывания.
    """

    @functools.wraps(func)
    def wrapper() -> int:
        try:
            code = func()
            return 0 if code is None else code
        except KeyboardInterrupt:
            print("Остановлено пользователем (Ctrl+C)", file=sys.stderr)
            return 130
        except Exception as e:
            if os.environ.get("HN_DEBUG") == "1":
                traceback.print_exc()
            print(f"Ошибка: {e}", file=sys.stderr)
            return 1

    return wrapper
