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
from ..sound import (
    Sound_halt_channel,
    Sound_make_working_chunk,
    Sound_play,
    Sound_play_chunk_loop,
    Sound_play_working_chunk,
    Sound_resample_working_chunk,
    EngineSound_create,
    EngineSound_delete,
    EngineSound_play,
    EngineSound_stop,
    EngineSound_update,
)
from .explosion_object import CExplosionObject
from .particle_explosion_object import CParticleExplosion

EXPLOSION_TILES = 1

# Pre-computed tyre coordinates for all 8 car angles (0-7)
# Each entry contains: (x1, y1, x2, y2) for left and right tyres
_TYRE_COORDS_TABLE = [
    (6, 7, 21, 7),    # 0° - straight
    (16, 3, 27, 12),  # 45°
    (23, 8, 23, 22),  # 90°
    (27, 16, 16, 25), # 135°
    (21, 25, 6, 25),  # 180° - upside down
    (5, 25, 16, 16),  # 225°
    (8, 22, 8, 8),    # 270°
    (5, 12, 16, 3),   # 315°
]

# Pre-computed car tile lookup for angles 0-359
_CAR_TILE_CACHE = {}
_NTILES_MINUS_EXPLOSION = 8  # Will be set properly in __init__


class CPlayerCarObject(CCarObject):
    def __init__(self, x: int, y: int, tiles, first_tile: int, last_tile: int, lk: int, rk: int, fk: int, score: int, init_delay: int, game):
        super().__init__(x, y, None, game)
        self.tiles = [tiles[index] for index in range(first_tile, last_tile + 1)]
        self.ntiles = len(self.tiles)
        # Pre-compute tiles minus explosion for car_tile calculation
        self._ntiles_minus_explosion = self.ntiles - EXPLOSION_TILES
        self.tile = self.car_tile(0)
        self.old_angle = 0
        self.rotating_angle = 0
        self.constitution = CONSTITUTION_PLAYER | CONSTITUTION_CAR
        self.fuel = const.MAX_FUEL
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
        self._skid_factor = 1.0
        # New SDL-based continuous looping engine sound
        self.engine_sound_player = EngineSound_create(self.game.S_carengine)
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
                cx = self.x + self.get_dx() // 2
                cy = self.y + self.get_dy() // 2
                self.game.objects.Add(CParticleExplosion(cx, cy, self.game))
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
        # Determine panning based on player count
        if self.game.focusing_objects.Length() == 1:
            pan = "both"
        elif self.game.focusing_objects[0] is self:
            pan = "right_only"
        else:
            pan = "left_only"

        # Update engine sound using SDL-based continuous looping
        if self.state != 4 and self.y > 0 and self.fuel > 0 and self.engine_sound_player is not None:
            speed_ratio = float(-self.y_speed) / MAX_SPEED if MAX_SPEED else 0.0
            speed_ratio = max(0.0, min(1.0, speed_ratio))

            if not self.engine_sound_player.is_playing:
                self.engine_sound_player.set_pan(pan)
                self.engine_sound_player.update_pitch(speed_ratio)
                self.enginesound_channel = EngineSound_play(self.engine_sound_player, speed_ratio, pan)
            elif (self.sound_timmer & 0x07) == 0:
                # Update pitch periodically (every 8 frames)
                self.engine_sound_player.set_pan(pan)
                EngineSound_update(self.engine_sound_player, speed_ratio)

            # Handle skid sound using SDL2 native looping
            if self.state in (5, 6) and self.game.S_carskid:
                skid_factor = 1.0 if self.state_timmer < 16 else 1.5
                # Only resample and restart when factor changes or not playing
                if self.skidsound_channel == -1 or abs(self._skid_factor - skid_factor) > 0.01:
                    self._skid_factor = skid_factor
                    Sound_resample_working_chunk(self.game.S_carskid, self.S_carskid_working, skid_factor, "both")
                    if self.skidsound_channel != -1:
                        Sound_halt_channel(self.skidsound_channel)
                    self.skidsound_channel = Sound_play_chunk_loop(self.S_carskid_working, -1)
            elif self.skidsound_channel != -1:
                Sound_halt_channel(self.skidsound_channel)
                self.skidsound_channel = -1
                self._skid_factor = 1.0
        else:
            # Stop engine sound when not driving
            if self.engine_sound_player is not None and self.engine_sound_player.is_playing:
                EngineSound_stop(self.engine_sound_player)
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
        # Use pre-computed tile lookup for better performance
        # Normalize angle to 0-359 range
        angle = angle % 360
        # Use pre-computed value instead of calculating ntiles - EXPLOSION_TILES
        return (angle * self._ntiles_minus_explosion) // 360

    def tyre_coordinates(self, angle: int):
        # Use pre-computed tyre coordinates table for better performance
        # Normalize angle to 0-359 range
        angle = angle % 360
        # Use pre-computed value instead of calculating ntiles - EXPLOSION_TILES
        tmp = angle * self._ntiles_minus_explosion / 360.0
        tile = int(tmp)
        fraction = tmp - tile
        tile2 = (tile + 1) % 8
        
        # Get base coordinates from lookup table
        x1a, y1a, x2a, y2a = _TYRE_COORDS_TABLE[tile]
        x1b, y1b, x2b, y2b = _TYRE_COORDS_TABLE[tile2]
        
        # Linear interpolation between angles
        inv_frac = 1.0 - fraction
        x1 = int(x1b * fraction + x1a * inv_frac)
        y1 = int(y1b * fraction + y1a * inv_frac)
        x2 = int(x2b * fraction + x2a * inv_frac)
        y2 = int(y2b * fraction + y2a * inv_frac)
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

        self.game.create_tyre_mark(self.x + e, self.y + f, self.compute_next_x() + a, self.compute_next_y() + b)
        self.game.create_tyre_mark(self.x + g, self.y + h, self.compute_next_x() + c, self.compute_next_y() + d)
