"""Keyboard state wrapper that mimics the old SDL key array access."""

from __future__ import annotations

class KeyboardState:
    def __init__(self) -> None:
        self._pressed = {}
        # Map joystick virtual keys to physical keys for backward compatibility
        self._joystick_map: dict[int, int | None] = {
            0x1000: None,  # JOY_LEFT
            0x1001: None,  # JOY_RIGHT
            0x1002: None,  # JOY_FIRE
            0x1003: None,  # JOY_UP
            0x1004: None,  # JOY_DOWN
            0x1010: None,  # JOY2_LEFT
            0x1011: None,  # JOY2_RIGHT
            0x1012: None,  # JOY2_FIRE
            0x1013: None,  # JOY2_UP
            0x1014: None,  # JOY2_DOWN
        }

    def set_joystick_mapping(self, left_key: int, right_key: int, fire_key: int, joystick_id: int = 0) -> None:
        """Set which physical keys joystick input should map to."""
        base = 0x1000 + (joystick_id * 0x10)
        self._joystick_map[base] = left_key
        self._joystick_map[base + 1] = right_key
        self._joystick_map[base + 2] = fire_key

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
        return [key for key, pressed in self._pressed.items() if pressed and not other[key]]

    def changed_keys(self, other: "KeyboardState") -> list[int]:
        keys = set(self._pressed) | set(other._pressed)
        return [key for key in keys if self[key] != other[key]]
