"""Keyboard state wrapper that mimics the old SDL key array access."""

from __future__ import annotations
from .constants import *

class KeyboardState:
    def __init__(self) -> None:
        self._pressed = {}
        self._keys = {}
        self._joy_mapping: dict[int, list[int]] = {}

    def set_joy_mapping(self, mapping: dict[int, list[int]]) -> None:
        """Set the joystick-to-keyboard mapping.

        Args:
            mapping: Dictionary mapping keyboard keycodes to lists of joystick keycodes.
                    When a keyboard key is checked, its mapped joystick keys are also checked.
        """
        self._joy_mapping = mapping

    def set(self, keycode: int, pressed: bool) -> None:
        self._keys[keycode] = pressed
        self._pressed[keycode] = pressed

    def __getitem__(self, keycode: int) -> bool:
        # Check if the key is directly pressed
        if self._pressed.get(keycode, False):
            return True
        # Check if any mapped joystick key is pressed
        joy_keys = self._joy_mapping.get(keycode)
        if joy_keys:
            for joy_key in joy_keys:
                if self._pressed.get(joy_key, False):
                    return True
        return False

    def get(self, keycode: int, default: bool = False) -> bool:
        # Check physical key first
        if self._pressed.get(keycode, False):
            return True
        # Check if any mapped joystick key is pressed
        joy_keys = self._joy_mapping.get(keycode)
        if joy_keys:
            for joy_key in joy_keys:
                if self._pressed.get(joy_key, False):
                    return True
        return default

    def copy(self) -> "KeyboardState":
        clone = KeyboardState()
        clone._pressed = dict(self._pressed)
        clone._joy_mapping = dict(self._joy_mapping)
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
                elif (button == 1):
                    self._pressed[JOY_SELECT] = pressed
            else:
                if (button == 0):
                    self._pressed[JOY2_FIRE] = pressed
                elif (button == 1):
                    self._pressed[JOY2_SELECT] = pressed

    def set_joy_hat(self, which: int, hat: int, value: int) -> None:
        """Handle joystick hat/d-pad motion.

        Args:
            which: Joystick index (0 or 1)
            hat: Hat index
            value: Hat position (SDL_HAT_UP, SDL_HAT_DOWN, SDL_HAT_LEFT, SDL_HAT_RIGHT)
        """
        if which == 0:
            self._pressed[JOY_UP] = bool(value & 1)    # SDL_HAT_UP = 1
            self._pressed[JOY_RIGHT] = bool(value & 2)  # SDL_HAT_RIGHT = 2
            self._pressed[JOY_DOWN] = bool(value & 4)   # SDL_HAT_DOWN = 4
            self._pressed[JOY_LEFT] = bool(value & 8)   # SDL_HAT_LEFT = 8
        else:
            self._pressed[JOY2_UP] = bool(value & 1)
            self._pressed[JOY2_RIGHT] = bool(value & 2)
            self._pressed[JOY2_DOWN] = bool(value & 4)
            self._pressed[JOY2_LEFT] = bool(value & 8)

    def update() -> None:
        pass