"""Keyboard state wrapper that mimics the old SDL key array access."""

from __future__ import annotations
from .constants import *

class KeyboardState:
    def __init__(self) -> None:
        self._pressed = {}
        self._keys = {}

    def set(self, keycode: int, pressed: bool) -> None:
        self._keys[keycode] = pressed
        self._pressed[keycode] = pressed ## TODO map it

    def __getitem__(self, keycode: int) -> bool:
        return bool(self._pressed.get(keycode, False))

    def get(self, keycode: int, default: bool = False) -> bool:
        # Check physical key first
        physical_pressed = bool(self._pressed.get(keycode, default))
        return physical_pressed

    def trigger(self, keycode, alt: int) -> None:
        if bool(self._pressed.get(alt, False)):
            self._pressed[keycode] = True

    def copy(self) -> "KeyboardState":
        clone = KeyboardState()
        clone._pressed = dict(self._pressed)
        return clone

    def newly_pressed(self, other: "KeyboardState") -> list[int]:
        return [key for key, pressed in self._pressed.items() if pressed and not other[key]]

    def changed_keys(self, other: "KeyboardState") -> list[int]:
        keys = set(self._pressed) | set(other._pressed)
        return [key for key in keys if self[key] != other[key]]

    def set_joy_axis(self, which: int, axis: int, value: int) -> None:
        if which == 0:
            if axis == 0:  # X axis
                self._pressed[JOY_LEFT] = value < -JOY_deadzone
                self._pressed[JOY_RIGHT] = value > JOY_deadzone

            elif axis == 1:  # Y axis
                self._pressed[JOY_UP] = value < -JOY_deadzone
                self._pressed[JOY_DOWN] = value > JOY_deadzone
        else:
            if axis == 0:  # X axis
                self._pressed[JOY2_LEFT] = value < -JOY_deadzone
                self._pressed[JOY2_RIGHT] = value > JOY_deadzone

            elif axis == 1:  # Y axis
                self._pressed[JOY2_UP] = value < -JOY_deadzone
                self._pressed[JOY2_DOWN] = value > JOY_deadzone

    def set_joy_button(self, which: int, button: int, pressed: bool) -> None:
            if which == 0:
                if (button == 0):
                    self._pressed[JOY_FIRE] = pressed
                else:
                    self._pressed[JOY_SELECT] = pressed
            else:
                if (button == 0):
                    self._pressed[JOY2_FIRE] = pressed
                else:
                    self._pressed[JOY2_SELECT] = pressed

    def update() -> None:
        pass