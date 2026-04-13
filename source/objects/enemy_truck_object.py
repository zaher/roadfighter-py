"""CEnemyTruckObject port."""

from __future__ import annotations

import random

from ..constants import CONSTITUTION_CAR, CONSTITUTION_SOLID, ENEMY_HSPEED, ENEMY_SPEED, PLAYING_WINDOW
from ..object import CCarObject
from ..sound import Sound_play


class CEnemyTruckObject(CCarObject):
    def __init__(self, x: int, y: int, tile, start_delay: int, game):
        super().__init__(x, y, tile, game)
        self.state_timmer = start_delay
        self.following_right_border = True
        self.distance_to_border = -1
        self.constitution = CONSTITUTION_SOLID | CONSTITUTION_CAR
        self.advanced = False

    def cycle(self, keyboard, old_keyboard) -> bool:
        super().cycle(keyboard, old_keyboard)
        if self.state_timmer > 0:
            self.state_timmer -= 1
        if self.state == 0 and self.state_timmer == 0:
            self.state = 1

        if self.state != 0:
            self.y_speed = -ENEMY_SPEED
            self.x_speed = 0
            if self.game.object_collision(8, 0, self, CONSTITUTION_SOLID) is not None:
                self.x_speed = -ENEMY_HSPEED
            elif self.game.object_collision(-8, 0, self, CONSTITUTION_SOLID) is not None:
                self.x_speed = ENEMY_HSPEED

            if self.x_speed == 0 and self.distance_to_border != -1:
                distance = -1
                step = 0
                while distance == -1 and step <= self.distance_to_border + 8:
                    if self.following_right_border:
                        if self.game.object_collision(step, 0, self, CONSTITUTION_SOLID) is not None:
                            distance = step - 8
                    else:
                        if self.game.object_collision(-step, 0, self, CONSTITUTION_SOLID) is not None:
                            distance = step - 8
                    step += 8
                if distance == -1:
                    distance = self.distance_to_border + 8
                if self.following_right_border:
                    if distance <= self.distance_to_border - 8:
                        self.x_speed = -ENEMY_HSPEED
                    if distance >= self.distance_to_border + 8:
                        self.x_speed = ENEMY_HSPEED
                else:
                    if distance <= self.distance_to_border - 8:
                        self.x_speed = ENEMY_HSPEED
                    if distance >= self.distance_to_border + 8:
                        self.x_speed = -ENEMY_HSPEED
        else:
            self.y_speed = 0

        if self.game.min_distance_to_players(self.y) > PLAYING_WINDOW:
            return False

        if not self.advanced and self.game.min_distance_to_players(self.y) < 48 and self.y_speed != 0:
            self.advanced = True
            if self.game.S_caradvance and random.randrange(3) == 0:
                Sound_play(self.game.S_truck)

        return True
