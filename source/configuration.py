from __future__ import annotations

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
    try:
        with f1open(filename, "r", FileType.USERDATA) as handle:
            values = handle.read().strip().split()
    except FileNotFoundError:
        cfg = default_configuration()
        save_configuration(cfg, filename)
        return cfg
    if len(values) < 7:
        cfg = default_configuration()
        save_configuration(cfg, filename)
        return cfg
    return Configuration(
        left_key=int(values[0]),
        right_key=int(values[1]),
        fire_key=int(values[2]),
        up_key=int(values[3]),
        down_key=int(values[4]),
        left2_key=int(values[5]),
        right2_key=int(values[6]),
        fire2_key=int(values[7]),
        up2_key=int(values[8]),
        down2_key=int(values[9]),
        game_remake_extras=(int(values[10]) == 1),
    )


def save_configuration(cfg: Configuration, filename: str = "RoadFighter.cfg") -> None:
    with f1open(filename, "w", FileType.USERDATA) as handle:
        handle.write(f"{cfg.left_key} {cfg.right_key} {cfg.fire_key}\n")
        handle.write(f"{cfg.left2_key} {cfg.right2_key} {cfg.fire2_key}\n")
        handle.write("1\n" if cfg.game_remake_extras else "0\n")
