"""Joystick state wrapper that maps joystick input to virtual key codes."""

from __future__ import annotations

import sdl2

# Virtual key codes for joystick input - use values outside standard key range
JOY_LEFT = 0x1000
JOY_RIGHT = 0x1001
JOY_FIRE = 0x1002


class JoystickState:
    def __init__(self) -> None:
        self._pressed = {}
        self._axis_x = 0
        self._deadzone = 8000  # Deadzone for analog stick (0-32767)
        
    def set_axis(self, axis: int, value: int) -> None:
        if axis == 0:  # X axis
            self._axis_x = value
            
    def set_button(self, button: int, pressed: bool) -> None:
        if button == 0:  # Button 0 (A/X) as fire
            self._pressed[JOY_FIRE] = pressed
            
    def update(self) -> None:
        # Update left/right based on axis position
        self._pressed[JOY_LEFT] = self._axis_x < -self._deadzone
        self._pressed[JOY_RIGHT] = self._axis_x > self._deadzone
            
    def __getitem__(self, keycode: int) -> bool:
        return bool(self._pressed.get(keycode, False))

    def get(self, keycode: int, default: bool = False) -> bool:
        return bool(self._pressed.get(keycode, default))

    def copy(self) -> "JoystickState":
        clone = JoystickState()
        clone._pressed = dict(self._pressed)
        clone._axis_x = self._axis_x
        clone._deadzone = self._deadzone
        return clone

    def newly_pressed(self, other: "JoystickState") -> list[int]:
        return [key for key, pressed in self._pressed.items() if pressed and not other[key]]

    def changed_keys(self, other: "JoystickState") -> list[int]:
        keys = set(self._pressed) | set(other._pressed)
        return [key for key in keys if self[key] != other[key]]
