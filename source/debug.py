from __future__ import annotations

# Global debug flag
_debug_enabled = False


def set_debug(enabled: bool) -> None:
    """Enable or disable debug output."""
    global _debug_enabled
    _debug_enabled = enabled


def debug_print(message: str, *args: object) -> None:
    """Print a message only if debug mode is enabled."""
    if not _debug_enabled:
        return
    if args:
        message = message % args
    print(message)


def output_debug_message(message: str, *args: object) -> None:
    if args:
        message = message % args
    print(message, end="")
