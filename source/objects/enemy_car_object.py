"""CEnemyCarObject port."""

from __future__ import annotations

from ..constants import CONSTITUTION_CAR, CONSTITUTION_SOLID, ENEMY_HSPEED, ENEMY_SPEED, PLAYING_WINDOW
from ..object import CCarObject
from .explosion_object import CExplosionObject


class CEnemyCarObject(CCarObject):
    def __init__(self, x: int, y: int, tile, start_delay: int, game):
        super().__init__(x, y, tile, game)
        self.state_timmer = start_delay
        self.following_right_border = True
        self.distance_to_border = -1
        self.slide_direction = 0
        self.slide_speed = 0
        self.slide_timmer = 0

    def cycle(self, keyboard, old_keyboard) -> bool:
        super().cycle(keyboard, old_keyboard)

        if self.state_timmer > 0:
            self.state_timmer -= 1
        if self.state == 0 and self.state_timmer == 0:
            self.state = 1

        if self.last_collision is not None:
            self.slide_direction = 1 if self.last_collision.get_x() < self.x else -1
            self.slide_speed = min(self.last_collision.get_y_speed(), self.y_speed)
            self.slide_timmer = 8
            self.last_collision = None

        if self.state != 0:
            self.y_speed = -ENEMY_SPEED
            self.x_speed = 0
            if self.game.object_collision(8, 0, self, CONSTITUTION_SOLID) is not None:
                self.x_speed = -ENEMY_HSPEED
                self.slide_timmer = 0
            elif self.game.object_collision(-8, 0, self, CONSTITUTION_SOLID) is not None:
                self.x_speed = ENEMY_HSPEED
                self.slide_timmer = 0

            if self.slide_timmer > 0:
                self.slide_timmer -= 1
                self.x_speed = int(ENEMY_HSPEED) if self.slide_direction == 1 else -int(ENEMY_HSPEED)
                self.y_speed = self.slide_speed

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

            other = self.game.object_collision(0, 0, self, CONSTITUTION_SOLID)
            if other is not None and other.constitution_test(CONSTITUTION_CAR):
                self.game.objects.Add(CExplosionObject(self.x - 16, self.y - 32, self.game.explosion_tiles, 0, 11, self.game))
                return False

            other = self.game.object_collision(0, 0, self, CONSTITUTION_CAR)
            if other is not None:
                other.car_collision(self)
                self.car_collision(other)
        else:
            self.y_speed = 0

        return self.game.min_distance_to_players(self.y) <= PLAYING_WINDOW

