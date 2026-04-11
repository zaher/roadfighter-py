"""CEnemyFastCarObject port."""

from __future__ import annotations

from ..constants import CONSTITUTION_CAR, CONSTITUTION_SOLID, FENEMY_HSPEED, FENEMY_SPEED, PLAYING_WINDOW
from ..object import CCarObject
from .enemy_car_object import CEnemyCarObject


class CEnemyFastCarObject(CEnemyCarObject):
    def cycle(self, keyboard, old_keyboard) -> bool:
        CCarObject.cycle(self, keyboard, old_keyboard)

        if self.state_timmer > 0:
            self.state_timmer -= 1
        if self.state == 0 and self.state_timmer == 0:
            self.state = 1

        if self.last_collision is not None:
            self.slide_direction = 1 if self.last_collision.get_x() < self.x else -1
            self.slide_timmer = 8
            self.last_collision = None

        if self.state != 0:
            self.y_speed = -FENEMY_SPEED
            self.x_speed = 0
            if self.game.object_collision(8, -32, self, CONSTITUTION_SOLID) is not None:
                self.x_speed = -FENEMY_HSPEED
                self.slide_timmer = 0
            elif self.game.object_collision(-8, -32, self, CONSTITUTION_SOLID) is not None:
                self.x_speed = FENEMY_HSPEED
                self.slide_timmer = 0

            if self.slide_timmer > 0:
                self.slide_timmer -= 1
                self.x_speed = FENEMY_HSPEED if self.slide_direction == 1 else -FENEMY_HSPEED

            if self.x_speed == 0:
                if (
                    self.game.object_collision(16, -64, self, CONSTITUTION_CAR) is not None
                    or self.game.object_collision(16, -32, self, CONSTITUTION_CAR) is not None
                    or self.game.object_collision(16, 0, self, CONSTITUTION_CAR) is not None
                ):
                    self.x_speed = -FENEMY_HSPEED
                    self.slide_timmer = 0
                elif (
                    self.game.object_collision(-16, -64, self, CONSTITUTION_CAR) is not None
                    or self.game.object_collision(-16, -32, self, CONSTITUTION_CAR) is not None
                    or self.game.object_collision(-16, 0, self, CONSTITUTION_CAR) is not None
                ):
                    self.x_speed = FENEMY_HSPEED
                    self.slide_timmer = 0

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
                        self.x_speed = -FENEMY_HSPEED
                    if distance >= self.distance_to_border + 8:
                        self.x_speed = FENEMY_HSPEED
                else:
                    if distance <= self.distance_to_border - 8:
                        self.x_speed = FENEMY_HSPEED
                    if distance >= self.distance_to_border + 8:
                        self.x_speed = -FENEMY_HSPEED

            other = self.game.object_collision(0, 0, self, CONSTITUTION_CAR)
            if other is not None:
                other.car_collision(self)
                self.car_collision(other)
        else:
            self.y_speed = 0

        return self.game.min_distance_to_players(self.y) <= PLAYING_WINDOW

