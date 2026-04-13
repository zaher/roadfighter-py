"""Keyboard state wrapper that mimics the old SDL key array access."""

from __future__ import annotations


class KeyboardState:
    def __init__(self) -> None:
        self._pressed = {}

    def set(self, keycode: int, pressed: bool) -> None:
        self._pressed[keycode] = pressed

    def __getitem__(self, keycode: int) -> bool:
        return bool(self._pressed.get(keycode, False))

    def get(self, keycode: int, default: bool = False) -> bool:
        return bool(self._pressed.get(keycode, default))

    def copy(self) -> "KeyboardState":
        clone = KeyboardState()
        clone._pressed = dict(self._pressed)
        return clone

    def newly_pressed(self, other: "KeyboardState") -> list[int]:
        return [key for key, pressed in self._pressed.items() if pressed and not other[key]]

    def changed_keys(self, other: "KeyboardState") -> list[int]:
        keys = set(self._pressed) | set(other._pressed)
        return [key for key in keys if self[key] != other[key]]
