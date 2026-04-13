"""CPlayerCarObject port."""

from __future__ import annotations

import math

from .. import constants as const
from ..constants import (
    BOUNCE_HSPEED,
    BRAKE_RATE,
    BRAKE_RATE_NO_FUEL,
    CONSTITUTION_CAR,
    CONSTITUTION_FUEL,
    CONSTITUTION_OIL,
    CONSTITUTION_PLAYER,
    CONSTITUTION_SOLID,
    CONSTITUTION_WATER,
    ENEMY_SPEED,
    MAX_ACCEL_RATE,
    MAX_HSPEED,
    MAX_SPEED,
    MIN_SPEED,
)
from ..object import CCarObject
from ..sound import Sound_halt_channel, Sound_make_working_chunk, Sound_play, Sound_play_working_chunk, Sound_resample_working_chunk
from .explosion_object import CExplosionObject

EXPLOSION_TILES = 1


class CPlayerCarObject(CCarObject):
    def __init__(self, x: int, y: int, tiles, first_tile: int, last_tile: int, lk: int, rk: int, fk: int, score: int, init_delay: int, game):
        super().__init__(x, y, None, game)
        self.tiles = [tiles[index] for index in range(first_tile, last_tile + 1)]
        self.ntiles = len(self.tiles)
        self.tile = self.car_tile(0)
        self.old_angle = 0
        self.rotating_angle = 0
        self.constitution = CONSTITUTION_PLAYER | CONSTITUTION_CAR
        self.fuel = int(const.MAX_FUEL * 0.95)
        self.score = score
        self.left_key = lk
        self.right_key = rk
        self.fire_key = fk
        self.state = 0
        self.state_timmer = init_delay
        self.blinking_time = init_delay
        self.bonus = 0
        self.next_bonus = 300
        self.bonus_timmer = 0
        self.sound_timmer = 0
        self.enginesound_channel = -1
        self.skidsound_channel = -1
        self.S_carengine_working, self._engine_buffer = Sound_make_working_chunk(self.game.S_carengine)
        self.S_carskid_working, self._skid_buffer = Sound_make_working_chunk(self.game.S_carskid)
        self.goal_reached = False

    def get_fuel(self) -> int:
        return self.fuel

    def get_score(self) -> int:
        return self.score

    def cycle(self, keyboard, old_keyboard) -> bool:
        speed_ratio = float(-self.y_speed) / MAX_SPEED if MAX_SPEED else 0.0

        if self.bonus_timmer > 0:
            self.bonus_timmer -= 1

        if self.last_collision is not None:
            if self.state != 4:
                self.state = 5 if self.last_collision.get_x() < self.x else 6
                self.state_timmer = 0
            self.last_collision = None

        if self.state == 0:
            self.rotating_angle = 0
            self.x_speed = 0
            self.y_speed = 0
            self.state_timmer -= 1
            if self.state_timmer == 0:
                self.state = 1

        elif self.state == 1:
            self.rotating_angle = 0
            self.tile = self.car_tile(0)
            if self.y > -32:
                self.score += (-self.y_speed) >> 10
                if self.goal_reached and self.y_speed < ENEMY_SPEED:
                    self.y_speed += MAX_ACCEL_RATE
                else:
                    if self.fuel > 0:
                        if keyboard[self.fire_key]:
                            acceleration_ratio = float(-self.y_speed) / MAX_SPEED if MAX_SPEED else 0.0
                            self.y_speed += int((1.0 - acceleration_ratio) * MAX_ACCEL_RATE)
                        else:
                            self.y_speed += BRAKE_RATE
                    else:
                        self.y_speed += BRAKE_RATE_NO_FUEL

                if speed_ratio < 0.1:
                    speed_ratio *= 2
                else:
                    speed_ratio = (((speed_ratio - 0.1) / 0.9) * 0.8) + 0.2

                if keyboard[self.left_key]:
                    if (not keyboard[self.right_key]) or (not old_keyboard[self.left_key]) or (self.x_speed < 0 and not old_keyboard[self.right_key]):
                        self.x_speed = -int(MAX_HSPEED * speed_ratio)
                if keyboard[self.right_key]:
                    if (not keyboard[self.left_key]) or (not old_keyboard[self.right_key]) or (self.x_speed > 0 and not old_keyboard[self.left_key]):
                        self.x_speed = int(MAX_HSPEED * speed_ratio)
                if not keyboard[self.right_key] and not keyboard[self.left_key]:
                    self.x_speed = 0
            else:
                self.y_speed += BRAKE_RATE_NO_FUEL

        elif self.state == 2:
            self.rotating_angle = 0
            self.tile = self.car_tile(0)
            if self.y > 0:
                self.score += (-self.y_speed) >> 10
                if self.fuel > 0:
                    if keyboard[self.fire_key]:
                        acceleration_ratio = float(-self.y_speed) / MAX_SPEED if MAX_SPEED else 0.0
                        self.y_speed += int((1.0 - acceleration_ratio) * MAX_ACCEL_RATE)
                    else:
                        self.y_speed += BRAKE_RATE
                else:
                    self.y_speed += BRAKE_RATE_NO_FUEL
            else:
                self.y_speed += BRAKE_RATE_NO_FUEL
            self.x_speed = BOUNCE_HSPEED
            self.state_timmer += 1
            if self.state_timmer >= 10:
                self.state = 1

        elif self.state == 3:
            self.rotating_angle = 0
            self.tile = self.car_tile(0)
            if self.y > 0:
                self.score += (-self.y_speed) >> 10
                if self.fuel > 0:
                    if keyboard[self.fire_key]:
                        acceleration_ratio = float(-self.y_speed) / MAX_SPEED if MAX_SPEED else 0.0
                        self.y_speed += int((1.0 - acceleration_ratio) * MAX_ACCEL_RATE)
                    else:
                        self.y_speed += BRAKE_RATE
                else:
                    self.y_speed += BRAKE_RATE_NO_FUEL
            else:
                self.y_speed += BRAKE_RATE_NO_FUEL
            self.x_speed = -BOUNCE_HSPEED
            self.state_timmer += 1
            if self.state_timmer >= 10:
                self.state = 1

        elif self.state == 4:
            if self.state_timmer == 0:
                self.game.objects.Add(CExplosionObject(self.x - 16, self.y - 32, self.game.explosion_tiles, 0, 11, self.game))
            self.rotating_angle = 0
            self.next_bonus = 300
            self.x_speed = 0
            self.y_speed = 0
            self.state_timmer += 1
            self.tile = self.ntiles - 1
            if self.state_timmer >= 75:
                self.blinking_time = 32
                self.tile = self.car_tile(0)
                self.state = 1
                self._recenter_after_explosion()

        elif self.state == 5:
            self.x_speed = MAX_HSPEED
            if self.state_timmer < 16:
                if keyboard[self.right_key] and not old_keyboard[self.right_key]:
                    self.state = 1
                self.rotating_angle = -45
            else:
                if (-self.y_speed) <= 0.75 * MAX_SPEED:
                    self.state = 1
                else:
                    self.rotating_angle -= 10
            self.tile = self.car_tile(self.rotating_angle)
            self.state_timmer += 1

        elif self.state == 6:
            self.x_speed = -MAX_HSPEED
            if self.state_timmer < 16:
                if keyboard[self.left_key] and not old_keyboard[self.left_key]:
                    self.state = 1
                self.rotating_angle = 45
            else:
                if (-self.y_speed) <= 0.75 * MAX_SPEED:
                    self.state = 1
                else:
                    self.rotating_angle += 10
            self.tile = self.car_tile(self.rotating_angle)
            self.state_timmer += 1

        self.sound_timmer += 1
        if self.fuel < int(0.15 * const.MAX_FUEL) and self.fuel > 0 and (self.sound_timmer % 45) == 0:
            if self.game.S_fuelempty:
                Sound_play(self.game.S_fuelempty)

        self._update_engine_audio()

        if self.state not in (4, 0):
            if self.goal_reached and self.fuel <= 0:
                self.fuel = 1

            if self.fuel > 0 and not self.goal_reached:
                self.fuel -= 1
                self.fuel = max(0, min(const.MAX_FUEL, self.fuel))

            obj = self.game.object_collision(0, 0, self, CONSTITUTION_FUEL)
            if obj is not None:
                self.fuel += const.FUEL_RECHARGE
                self.fuel = min(const.MAX_FUEL, self.fuel)
                self.game.todelete.Add(obj)
                self.bonus = self.next_bonus
                self.score += self.next_bonus
                self.bonus_timmer = 64
                if self.next_bonus == 800:
                    self.next_bonus = 1000
                elif self.next_bonus == 500:
                    self.next_bonus = 800
                elif self.next_bonus == 300:
                    self.next_bonus = 500
                if self.game.S_takefuel:
                    Sound_play(self.game.S_takefuel)

            obj = self.game.object_collision(0, 0, self, CONSTITUTION_SOLID)
            if obj is not None:
                if (-self.y_speed) > 0.75 * MAX_SPEED or obj.constitution_test(CONSTITUTION_CAR):
                    if self.fuel > const.FUEL_LOSS * 2:
                        self.fuel -= const.FUEL_LOSS
                    self.state = 4
                    self.state_timmer = 0
                    self.y_speed = 0
                    self.x_speed = 0
                    if self.game.S_crash:
                        Sound_play(self.game.S_crash)
                elif self.game.object_collision(8, 0, self, CONSTITUTION_SOLID) is not None:
                    self.state_timmer = 0
                    self.state = 3
                    if self.game.S_collision:
                        Sound_play(self.game.S_collision)
                elif self.game.object_collision(-8, 0, self, CONSTITUTION_SOLID) is not None:
                    self.state_timmer = 0
                    self.state = 2
                    if self.game.S_collision:
                        Sound_play(self.game.S_collision)
                else:
                    self.state = 4
                    self.state_timmer = 0
                    self.y_speed = 0
                    self.x_speed = 0
                    if self.game.S_crash:
                        Sound_play(self.game.S_crash)
            else:
                obj = self.game.object_collision(0, 0, self, CONSTITUTION_CAR)
                if obj is not None:
                    if self.last_collision is None and self.game.S_collision:
                        Sound_play(self.game.S_collision)
                    obj.car_collision(self)
                    self.car_collision(obj)
                else:
                    obj = self.game.object_collision(0, 0, self, CONSTITUTION_OIL)
                    if obj is not None and (-self.y_speed) > 0.75 * MAX_SPEED:
                        self.last_collision = self
                    else:
                        obj = self.game.object_collision(0, 0, self, CONSTITUTION_WATER)
                        if obj is not None and (-self.y_speed) > 0.75 * MAX_SPEED:
                            if self.game.S_water:
                                Sound_play(self.game.S_water)
                            self.y_speed = -int(0.5 * MAX_SPEED)

        if self.blinking_time > 0:
            self.blinking_time -= 1

        if self.y_speed > -MIN_SPEED:
            self.y_speed = -MIN_SPEED
        if self.y_speed < -MAX_SPEED:
            self.y_speed = -MAX_SPEED

        if self.game.game_remake_extras and self.state in (5, 6) and self.tile < 8:
            self._add_tyre_marks()

        super().cycle(keyboard, old_keyboard)

        if self.y < -33:
            self.y = -33

        self.old_angle = self.rotating_angle
        return True

    def _update_engine_audio(self) -> None:
        if self.state != 4 and self.y > 0 and self.fuel > 0 and self.game.S_carengine and (self.sound_timmer & 0x07) == 0:
            factor = 0.8408964 + (1.259921 - 0.8408964) * (float(-self.y_speed) / MAX_SPEED)
            factor = max(0.8408964, min(1.2599210, factor))

            if self.game.focusing_objects.Length() == 1:
                pan = "both"
            elif self.game.focusing_objects[0] == self:
                pan = "right_only"
            else:
                pan = "left_only"

            Sound_resample_working_chunk(self.game.S_carengine, self.S_carengine_working, factor, pan)
            if self.enginesound_channel == -1:
                self.enginesound_channel = Sound_play_working_chunk(self.S_carengine_working, -1)
            else:
                self.enginesound_channel = Sound_play_working_chunk(self.S_carengine_working, self.enginesound_channel)

            if self.state in (5, 6) and self.game.S_carskid:
                skid_factor = 1.0 if self.state_timmer < 16 else 1.5
                Sound_resample_working_chunk(self.game.S_carskid, self.S_carskid_working, skid_factor, "both")
                if self.skidsound_channel == -1:
                    self.skidsound_channel = Sound_play_working_chunk(self.S_carskid_working, -1)
                else:
                    self.skidsound_channel = Sound_play_working_chunk(self.S_carskid_working, self.skidsound_channel)
            elif self.skidsound_channel != -1:
                Sound_halt_channel(self.skidsound_channel)
                self.skidsound_channel = -1
        else:
            if self.enginesound_channel != -1:
                Sound_halt_channel(self.enginesound_channel)
                self.enginesound_channel = -1
            if self.skidsound_channel != -1:
                Sound_halt_channel(self.skidsound_channel)
                self.skidsound_channel = -1

    def draw(self, sx: int, sy: int, screen) -> None:
        self.draw_x = self.x
        self.draw_y = self.y
        if 0 <= self.tile < self.ntiles:
            if self.blinking_time > 0:
                factor = int(math.sin(float(self.blinking_time) / 2.0) * 50 + 50)
                self.tiles[self.tile].draw_shaded(self.x - sx, self.y - sy, screen, factor, -1, -1, -1, 0)
            else:
                self.tiles[self.tile].draw(self.x - sx, self.y - sy, screen)

        if self.fuel <= 0:
            self.game.extra_tiles[1].draw(
                (self.x - sx) + 16 - self.game.extra_tiles[1].get_dx() // 2,
                (self.y - sy) - self.game.extra_tiles[1].get_dy(),
                screen,
            )
        elif self.bonus > 0 and self.bonus_timmer > 0:
            index = 2
            if self.bonus == 500:
                index = 3
            if self.bonus == 800:
                index = 4
            if self.bonus == 1000:
                index = 5
            self.game.extra_tiles[index].draw(
                (self.x - sx) + 16 - self.game.extra_tiles[index].get_dx() // 2,
                (self.y - sy) - self.game.extra_tiles[index].get_dy(),
                screen,
            )

    def car_tile(self, angle: int) -> int:
        nt = self.ntiles - EXPLOSION_TILES
        while angle < 0:
            angle += 360
        while angle >= 360:
            angle -= 360
        return (angle * nt) // 360

    def tyre_coordinates(self, angle: int):
        x1v = [6, 16, 23, 27, 21, 16, 8, 5]
        y1v = [7, 3, 8, 16, 25, 25, 22, 12]
        x2v = [21, 27, 23, 16, 6, 5, 8, 16]
        y2v = [7, 12, 22, 25, 25, 16, 8, 3]
        nt = self.ntiles - EXPLOSION_TILES
        while angle < 0:
            angle += 360
        while angle >= 360:
            angle -= 360
        tmp = float(angle) * float(nt) / 360.0
        tile = int(math.floor(tmp))
        fraction = tmp - tile
        tile2 = (tile + 1) % 8
        x1 = int(x1v[tile2] * fraction + x1v[tile] * (1.0 - fraction))
        y1 = int(y1v[tile2] * fraction + y1v[tile] * (1.0 - fraction))
        x2 = int(x2v[tile2] * fraction + x2v[tile] * (1.0 - fraction))
        y2 = int(y2v[tile2] * fraction + y2v[tile] * (1.0 - fraction))
        return x1, y1, x2, y2

    def reach_goal(self) -> None:
        self.goal_reached = True

    def _recenter_after_explosion(self) -> None:
        if self.game.object_collision(8, 0, self, CONSTITUTION_SOLID) is None:
            found = False
            j = self.game.get_dx() // 2
            for offset in range(4, self.game.get_dx() - self.draw_x, 4):
                if self.game.object_collision(offset, 0, self, CONSTITUTION_SOLID) is not None:
                    j = self.x + offset
                    found = True
                    break
            if found:
                self.draw_x = self.x = ((self.draw_x + 4) + (j - 4)) // 2
            else:
                self.draw_x = self.x = (self.game.get_dx() // 2) - 16
        elif self.game.object_collision(-8, 0, self, CONSTITUTION_SOLID) is None:
            found = False
            j = self.game.get_dx() // 2
            for offset in range(-4, -self.draw_x, -4):
                if self.game.object_collision(offset, 0, self, CONSTITUTION_SOLID) is not None:
                    j = self.x + offset
                    found = True
                    break
            if found:
                self.draw_x = self.x = ((self.draw_x - 4) + (j + 4)) // 2
            else:
                self.draw_x = self.x = (self.game.get_dx() // 2) - 16
        else:
            self.draw_x = self.x = (self.game.get_dx() // 2) - 8

    def _add_tyre_marks(self) -> None:
        a, b, c, d = self.tyre_coordinates(self.rotating_angle)
        e, f, g, h = self.tyre_coordinates(self.old_angle)

        first_mark = self.game.create_tyre_mark(self.x + e, self.y + f, self.compute_next_x() + a, self.compute_next_y() + b)
        if first_mark is not None:
            self.game.tyre_marks.Add(first_mark)

        second_mark = self.game.create_tyre_mark(self.x + g, self.y + h, self.compute_next_x() + c, self.compute_next_y() + d)
        if second_mark is not None:
            self.game.tyre_marks.Add(second_mark)
