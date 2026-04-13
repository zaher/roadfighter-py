from __future__ import annotations


def output_debug_message(message: str, *args: object) -> None:
    if args:
        message = message % args
    print(message, end="")
