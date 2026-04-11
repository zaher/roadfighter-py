"""CFuelObject port."""

from __future__ import annotations

from ..constants import CONSTITUTION_FUEL, ENEMY_HSPEED, ENEMY_SPEED, PLAYING_WINDOW, CONSTITUTION_SOLID
from ..object import CObject


class CFuelObject(CObject):
    def __init__(self, x: int, y: int, tile, game):
        super().__init__(x, y, tile, CONSTITUTION_FUEL, game)
        self.y_precision = 0
        self.x_precision = 0
        self.y_speed = 0
        self.x_speed = 0

    def cycle(self, keyboard, old_keyboard) -> bool:
        self.y_precision += self.y_speed
        while self.y_precision > (1 << 8):
            self.y += 1
            self.y_precision -= 1 << 8
        while self.y_precision < ((-1) << 8):
            self.y -= 1
            self.y_precision += 1 << 8

        self.x_precision += self.x_speed
        while self.x_precision > (1 << 8):
            self.x += 1
            self.x_precision -= 1 << 8
        while self.x_precision < ((-1) << 8):
            self.x -= 1
            self.x_precision += 1 << 8

        self.y_speed = -ENEMY_SPEED
        self.x_speed = 0
        if self.game.object_collision(16, 0, self, CONSTITUTION_SOLID) is not None:
            self.x_speed = -ENEMY_HSPEED
        elif self.game.object_collision(-16, 0, self, CONSTITUTION_SOLID) is not None:
            self.x_speed = ENEMY_HSPEED

        return self.game.min_distance_to_players(self.y) <= PLAYING_WINDOW

