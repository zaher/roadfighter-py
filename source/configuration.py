from __future__ import annotations

import configparser
from dataclasses import dataclass
import sdl2

from .constants import (
    DEFAULT_FIRE_KEY,
    DEFAULT_FIRE2_KEY,
    DEFAULT_LEFT_KEY,
    DEFAULT_LEFT2_KEY,
    DEFAULT_RIGHT_KEY,
    DEFAULT_RIGHT2_KEY,
    DEFAULT_UP_KEY,
    DEFAULT_UP2_KEY,
    DEFAULT_DOWN_KEY,
    DEFAULT_DOWN2_KEY,
)
from .filehandling import FileType, f1open


def keycode_to_name(keycode: int) -> str:
    """Convert SDL keycode to human-readable string name."""
    name = sdl2.SDL_GetKeyName(keycode)
    if isinstance(name, bytes):
        return name.decode("utf-8", "ignore")
    return str(name)


def name_to_keycode(name: str) -> int:
    """Convert human-readable key name to SDL keycode."""
    return sdl2.SDL_GetKeyFromName(name.encode("utf-8"))


@dataclass
class Configuration:
    left_key: int
    right_key: int
    fire_key: int
    up_key: int
    down_key: int
    left2_key: int
    right2_key: int
    fire2_key: int
    up2_key: int
    down2_key: int
    game_remake_extras: bool


def default_configuration() -> Configuration:
    return Configuration(
        left_key=DEFAULT_LEFT_KEY,
        right_key=DEFAULT_RIGHT_KEY,
        fire_key=DEFAULT_FIRE_KEY,
        up_key=DEFAULT_UP_KEY,
        down_key=DEFAULT_DOWN_KEY,
        left2_key=DEFAULT_LEFT2_KEY,
        right2_key=DEFAULT_RIGHT2_KEY,
        fire2_key=DEFAULT_FIRE2_KEY,
        up2_key=DEFAULT_UP2_KEY,
        down2_key=DEFAULT_DOWN2_KEY,
        game_remake_extras=True,
    )


def load_configuration(filename: str = "RoadFighter.cfg") -> Configuration:
    config = configparser.ConfigParser()
    
    try:
        with f1open(filename, "r", FileType.USERDATA) as handle:
            config.read_file(handle)
    except (FileNotFoundError, configparser.Error):
        cfg = default_configuration()
        save_configuration(cfg, filename)
        return cfg
    
    try:
        keys_section = config["Keys"]
        game_section = config["Game"]
        
        def get_key(name: str) -> int:
            value = keys_section[name]
            try:
                # Handle old numeric format for backwards compatibility
                return int(value)
            except ValueError:
                # New string format
                keycode = name_to_keycode(value)
                if keycode == sdl2.SDLK_UNKNOWN:
                    # Fallback to default if key not recognized
                    raise ValueError(f"Unknown key name: {value}")
                return keycode
        
        return Configuration(
            left_key=get_key("left"),
            right_key=get_key("right"),
            fire_key=get_key("fire"),
            up_key=get_key("up"),
            down_key=get_key("down"),
            left2_key=get_key("left2"),
            right2_key=get_key("right2"),
            fire2_key=get_key("fire2"),
            up2_key=get_key("up2"),
            down2_key=get_key("down2"),
            game_remake_extras=game_section.getboolean("remake_extras"),
        )
    except (KeyError, ValueError):
        cfg = default_configuration()
        save_configuration(cfg, filename)
        return cfg


def save_configuration(cfg: Configuration, filename: str = "RoadFighter.cfg") -> None:
    config = configparser.ConfigParser()
    
    config["Keys"] = {
        "left": keycode_to_name(cfg.left_key),
        "right": keycode_to_name(cfg.right_key),
        "fire": keycode_to_name(cfg.fire_key),
        "up": keycode_to_name(cfg.up_key),
        "down": keycode_to_name(cfg.down_key),
        "left2": keycode_to_name(cfg.left2_key),
        "right2": keycode_to_name(cfg.right2_key),
        "fire2": keycode_to_name(cfg.fire2_key),
        "up2": keycode_to_name(cfg.up2_key),
        "down2": keycode_to_name(cfg.down2_key),
    }
    
    config["Game"] = {
        "remake_extras": "yes" if cfg.game_remake_extras else "no",
    }
    
    with f1open(filename, "w", FileType.USERDATA) as handle:
        config.write(handle)
