"""Keyboard state wrapper that mimics the old SDL key array access."""

from __future__ import annotations

import sdl2
from sdl2 import SDLK_UP, SDLK_DOWN


class KeyboardState:
    def __init__(self) -> None:
        self._pressed = {}
        # Map joystick virtual keys to physical keys for backward compatibility
        self._joystick_map: dict[int, int | None] = {
            0x1000: None,  # JOY_LEFT
            0x1001: None,  # JOY_RIGHT
            0x1002: None,  # JOY_FIRE
            0x1003: SDLK_UP,    # JOY_UP
            0x1004: SDLK_DOWN,  # JOY_DOWN
        }
        
    def set_joystick_mapping(self, left_key: int, right_key: int, fire_key: int) -> None:
        """Set which physical keys joystick input should map to."""
        self._joystick_map[0x1000] = left_key
        self._joystick_map[0x1001] = right_key
        self._joystick_map[0x1002] = fire_key

    def set(self, keycode: int, pressed: bool) -> None:
        self._pressed[keycode] = pressed

    def __getitem__(self, keycode: int) -> bool:
        # Check physical key first
        physical_pressed = bool(self._pressed.get(keycode, False))
        # Check if any joystick key is mapped to this physical key
        joystick_pressed = False
        for joy_key, mapped_key in self._joystick_map.items():
            if mapped_key == keycode:
                joystick_pressed = joystick_pressed or bool(self._pressed.get(joy_key, False))
        return physical_pressed or joystick_pressed

    def get(self, keycode: int, default: bool = False) -> bool:
        # Check physical key first
        physical_pressed = bool(self._pressed.get(keycode, default))
        # Check if any joystick key is mapped to this physical key
        joystick_pressed = False
        for joy_key, mapped_key in self._joystick_map.items():
            if mapped_key == keycode:
                joystick_pressed = joystick_pressed or bool(self._pressed.get(joy_key, False))
        return physical_pressed or joystick_pressed

    def copy(self) -> "KeyboardState":
        clone = KeyboardState()
        clone._pressed = dict(self._pressed)
        clone._joystick_map = dict(self._joystick_map)
        return clone

    def newly_pressed(self, other: "KeyboardState") -> list[int]:
        pressed = []
        # Check all actual keys
        for key, is_pressed in self._pressed.items():
            if is_pressed and not other[key]:
                pressed.append(key)
        # Check joystick mapped keys
        for joy_key, mapped_key in self._joystick_map.items():
            if mapped_key is not None and self[mapped_key] and not other[mapped_key]:
                if mapped_key not in pressed:
                    pressed.append(mapped_key)
        return pressed

    def changed_keys(self, other: "KeyboardState") -> list[int]:
        keys = set(self._pressed) | set(other._pressed)
        # Add joystick mapped keys
        for mapped_key in self._joystick_map.values():
            if mapped_key is not None:
                keys.add(mapped_key)
        return [key for key in keys if self[key] != other[key]]
