"""Keyboard state wrapper that mimics the old SDL key array access."""

from __future__ import annotations
from .constants import *

class KeyboardState:
    def __init__(self, is_network_game: bool = False, player_id: int = 0) -> None:
        self._pressed = {}
        self._keys = {}
        self._joy_mapping: dict[int, list[int]] = {}
        
        # Network multiplayer support
        self.is_network_game = is_network_game
        self.player_id = player_id  # 0 = local player, 1 = remote player
        self._remote_input: dict[str, bool] = {}  # Remote player input state
        self._input_buffer = None  # Will be set if using input buffering

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
        # If this is player 2 key in network game, use remote input
        if self.is_network_game and self._is_player2_key(keycode):
            action = None
            if keycode in (DEFAULT_LEFT2_KEY, JOY2_LEFT):
                action = 'left'
            elif keycode in (DEFAULT_RIGHT2_KEY, JOY2_RIGHT):
                action = 'right'
            elif keycode in (DEFAULT_UP2_KEY, JOY2_UP):
                action = 'up'
            elif keycode in (DEFAULT_DOWN2_KEY, JOY2_DOWN):
                action = 'down'
            elif keycode in (DEFAULT_FIRE2_KEY, JOY2_FIRE):
                action = 'fire'
            
            if action:
                return self._remote_input.get(action, False)
            return False
        
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
                else:
                    self._pressed[JOY_SELECT] = pressed
            else:
                if (button == 0):
                    self._pressed[JOY2_FIRE] = pressed
                else:
                    self._pressed[JOY2_SELECT] = pressed

    def set_remote_input(self, input_data: dict) -> None:
        """Set remote player input (from network)."""
        self._remote_input = input_data
    
    def get_player_input(self, player_idx: int) -> dict:
        """Get input for a specific player (for sending over network)."""
        if player_idx == 0:
            # Local player input - use default keys or joy mapping
            return {
                'left': self._pressed.get(DEFAULT_LEFT_KEY, False) or self._pressed.get(JOY_LEFT, False),
                'right': self._pressed.get(DEFAULT_RIGHT_KEY, False) or self._pressed.get(JOY_RIGHT, False),
                'up': self._pressed.get(DEFAULT_UP_KEY, False) or self._pressed.get(JOY_UP, False),
                'down': self._pressed.get(DEFAULT_DOWN_KEY, False) or self._pressed.get(JOY_DOWN, False),
                'fire': self._pressed.get(DEFAULT_FIRE_KEY, False) or self._pressed.get(JOY_FIRE, False),
            }
        else:
            # Return remote input
            return self._remote_input.copy() if self._remote_input else {
                'left': False, 'right': False, 'up': False, 'down': False, 'fire': False
            }
    
    def _is_player2_key(self, keycode: int) -> bool:
        """Check if a keycode belongs to player 2."""
        # Player 2 uses WASD + LSHIFT or JOY2 mappings
        player2_keys = {
            DEFAULT_LEFT2_KEY, DEFAULT_RIGHT2_KEY, DEFAULT_UP2_KEY, DEFAULT_DOWN2_KEY, DEFAULT_FIRE2_KEY,
            JOY2_LEFT, JOY2_RIGHT, JOY2_UP, JOY2_DOWN, JOY2_FIRE, JOY2_SELECT
        }
        return keycode in player2_keys
    
    def _map_action_to_key(self, action: str) -> int:
        """Map action name to keycode."""
        action_map = {
            'left': DEFAULT_LEFT2_KEY,
            'right': DEFAULT_RIGHT2_KEY,
            'up': DEFAULT_UP2_KEY,
            'down': DEFAULT_DOWN2_KEY,
            'fire': DEFAULT_FIRE2_KEY,
        }
        return action_map.get(action, 0)
    
    def update(self) -> None:
        pass