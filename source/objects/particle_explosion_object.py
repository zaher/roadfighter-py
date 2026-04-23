"""CParticleExplosion - fire-colored particle burst for car crashes."""

from __future__ import annotations

import math
import random

import sdl2
from ctypes import byref
from sdl2 import SDL_Rect

from ..constants import CONSTITUTION_NONE
from ..object import CObject


class CParticleExplosion(CObject):
    """A short-lived burst of fire-colored particles."""

    FIRE_COLORS = [
        0xFFFFFF00,  # bright yellow
        0xFFFFA500,  # orange
        0xFFFF0000,  # red
        0xFFFF6400,  # dark orange
    ]

    def __init__(self, x: int, y: int, game, count: int = 32) -> None:
        super().__init__(x, y, None, CONSTITUTION_NONE, game)
        self.particles: list[dict] = []
        for _ in range(count):
            angle = random.uniform(0.0, math.pi * 2.0)
            speed = random.uniform(1.5, 5.5)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            lifetime = random.randint(18, 35)
            color = random.choice(self.FIRE_COLORS)
            # Spawn within a small radius so they don't all start at the exact same pixel
            spawn_x = x + random.randint(-4, 4)
            spawn_y = y + random.randint(-4, 4)
            self.particles.append(
                {
                    "fx": float(spawn_x),
                    "fy": float(spawn_y),
                    "vx": vx,
                    "vy": vy,
                    "life": lifetime,
                    "max_life": lifetime,
                    "color": color,
                }
            )

    def cycle(self, keyboard, old_keyboard) -> bool:
        alive = False
        for p in self.particles:
            if p["life"] <= 0:
                continue
            p["fx"] += p["vx"]
            p["fy"] += p["vy"]
            # Air drag
            p["vx"] *= 0.92
            p["vy"] *= 0.92
            # Slight upward drift (fire rises) – negative y is up on screen
            p["vy"] -= 0.08
            p["life"] -= 1
            if p["life"] > 0:
                alive = True
        return alive

    def draw(self, sx: int, sy: int, screen) -> None:
        for p in self.particles:
            if p["life"] <= 0:
                continue
            px = int(p["fx"]) - sx
            py = int(p["fy"]) - sy
            # Particle shrinks as it dies
            size = max(1, (p["life"] * 3) // p["max_life"])
            rect = SDL_Rect(px, py, size, size)
            sdl2.SDL_FillRect(screen, byref(rect), p["color"])
