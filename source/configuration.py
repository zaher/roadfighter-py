from __future__ import annotations

import configparser
from dataclasses import dataclass

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
        
        return Configuration(
            left_key=int(keys_section["left"]),
            right_key=int(keys_section["right"]),
            fire_key=int(keys_section["fire"]),
            up_key=int(keys_section["up"]),
            down_key=int(keys_section["down"]),
            left2_key=int(keys_section["left2"]),
            right2_key=int(keys_section["right2"]),
            fire2_key=int(keys_section["fire2"]),
            up2_key=int(keys_section["up2"]),
            down2_key=int(keys_section["down2"]),
            game_remake_extras=game_section.getboolean("remake_extras"),
        )
    except (KeyError, ValueError):
        cfg = default_configuration()
        save_configuration(cfg, filename)
        return cfg


def save_configuration(cfg: Configuration, filename: str = "RoadFighter.cfg") -> None:
    config = configparser.ConfigParser()
    
    config["Keys"] = {
        "left": str(cfg.left_key),
        "right": str(cfg.right_key),
        "fire": str(cfg.fire_key),
        "up": str(cfg.up_key),
        "down": str(cfg.down_key),
        "left2": str(cfg.left2_key),
        "right2": str(cfg.right2_key),
        "fire2": str(cfg.fire2_key),
        "up2": str(cfg.up2_key),
        "down2": str(cfg.down2_key),
    }
    
    config["Game"] = {
        "remake_extras": "yes" if cfg.game_remake_extras else "no",
    }
    
    with f1open(filename, "w", FileType.USERDATA) as handle:
        config.write(handle)
